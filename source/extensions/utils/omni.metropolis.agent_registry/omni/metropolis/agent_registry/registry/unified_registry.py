"""Unified Model Registry for model registration."""

from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any

import carb
import yaml
from lc_agent import get_chat_model_registry

from ..agent_factory.model_factory import ModelFactory

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
_RETRYABLE_ERROR_PATTERNS = (
    "too many requests",
    "rate limit",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "timed out",
    "timeout",
    "connection reset",
)
# Sized against per-model rate limits on the public NVIDIA endpoint, where a throttled
# model needs roughly 20-30s of quiet before it serves again. The previous ceiling of 8s
# across 3 attempts expired well inside that window, so a burst of pipeline nodes could
# never recover and surfaced as a hard 429 failure.
_DEFAULT_MAX_RETRIES = 6
_DEFAULT_INITIAL_RETRY_DELAY_SECONDS = 2.0
_DEFAULT_MAX_RETRY_DELAY_SECONDS = 45.0
_DEFAULT_RETRY_JITTER_FACTOR = 0.2


def _extract_status_code(exc: Exception) -> int | None:
    """Best-effort extraction of an HTTP-like status code from an exception."""
    for candidate in (exc, getattr(exc, "response", None)):
        if candidate is None:
            continue
        for attr_name in ("status_code", "status", "code"):
            value = getattr(candidate, attr_name, None)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

    for arg in getattr(exc, "args", ()):
        if isinstance(arg, dict):
            for key in ("status_code", "status", "code"):
                value = arg.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)

    match = re.search(r"\b(429|502|503|504)\b", str(exc))
    if match:
        return int(match.group(1))
    return None


def _extract_retry_after_seconds(exc: Exception) -> float | None:
    """Return a parsed ``Retry-After`` value when the provider exposes one."""
    for candidate in (exc, getattr(exc, "response", None)):
        headers = getattr(candidate, "headers", None)
        if not isinstance(headers, dict):
            continue
        value = headers.get("Retry-After") or headers.get("retry-after")
        if value is None:
            continue
        try:
            retry_after = float(value)
        except (TypeError, ValueError):
            continue
        if retry_after > 0:
            return retry_after
    return None


def _retryable_exception_types() -> tuple[type[BaseException], ...]:
    """Transport failures that identify themselves by type rather than message."""
    # aiohttp raises a bare ``asyncio.TimeoutError`` when its own read timer fires
    # (``raise asyncio.TimeoutError from exc_val``). Its ``str()`` is empty, so the
    # message patterns below - including "timeout" - never match and the call was
    # treated as permanent. On 3.11+ asyncio.TimeoutError is builtin TimeoutError.
    types: tuple[type[BaseException], ...] = (TimeoutError,)
    try:
        import aiohttp

        types += (aiohttp.ServerTimeoutError, aiohttp.ClientConnectionError)
    except ImportError:
        pass
    return types


def _is_retryable_exception(exc: Exception) -> bool:
    """Return whether an exception looks like a transient remote failure."""
    if isinstance(exc, _retryable_exception_types()):
        return True

    status_code = _extract_status_code(exc)
    if status_code in _RETRYABLE_STATUS_CODES:
        return True

    message = str(exc).strip().lower()
    return any(pattern in message for pattern in _RETRYABLE_ERROR_PATTERNS)


class RetryingChatModel:
    """Wrap a chat model with lightweight retry/backoff for transient failures."""

    def __init__(
        self,
        model: Any,
        *,
        model_name: str,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        initial_retry_delay_seconds: float = _DEFAULT_INITIAL_RETRY_DELAY_SECONDS,
        max_retry_delay_seconds: float = _DEFAULT_MAX_RETRY_DELAY_SECONDS,
        retry_jitter_factor: float = _DEFAULT_RETRY_JITTER_FACTOR,
    ) -> None:
        self._model = model
        self._model_name = str(model_name or "").strip() or "<unnamed-model>"
        self._max_retries = max(0, int(max_retries))
        self._initial_retry_delay_seconds = max(
            0.0,
            float(initial_retry_delay_seconds),
        )
        self._max_retry_delay_seconds = max(
            self._initial_retry_delay_seconds,
            float(max_retry_delay_seconds),
        )
        self._retry_jitter_factor = max(0.0, float(retry_jitter_factor))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)

    @property
    def base_model(self) -> Any:
        """Expose the wrapped model for diagnostics and focused tests."""
        return self._model

    def _compute_retry_delay(self, exc: Exception, *, retry_index: int) -> float:
        retry_after = _extract_retry_after_seconds(exc)
        if retry_after is not None:
            return retry_after

        base_delay = self._initial_retry_delay_seconds * (2 ** max(0, retry_index - 1))
        capped_delay = min(base_delay, self._max_retry_delay_seconds)
        if capped_delay <= 0 or self._retry_jitter_factor <= 0:
            return capped_delay

        jitter = random.uniform(0.0, capped_delay * self._retry_jitter_factor)
        return capped_delay + jitter

    def _log_retry(self, exc: Exception, *, retry_index: int, wait_seconds: float) -> None:
        status_code = _extract_status_code(exc)
        reason = f"status {status_code}" if status_code is not None else str(exc)
        carb.log_warn(
            f"[RetryingChatModel] Retryable failure for model '{self._model_name}' "
            f"({reason}). Retrying in {wait_seconds:.1f}s "
            f"({retry_index}/{self._max_retries})."
        )

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the wrapped model synchronously with retry/backoff."""
        if not hasattr(self._model, "invoke"):
            raise AttributeError(
                f"Wrapped model '{self._model_name}' does not support invoke()."
            )

        for retry_index in range(self._max_retries + 1):
            try:
                return self._model.invoke(*args, **kwargs)
            except Exception as exc:
                if retry_index >= self._max_retries or not _is_retryable_exception(exc):
                    raise
                wait_seconds = self._compute_retry_delay(
                    exc,
                    retry_index=retry_index + 1,
                )
                self._log_retry(
                    exc,
                    retry_index=retry_index + 1,
                    wait_seconds=wait_seconds,
                )
                time.sleep(wait_seconds)

        raise RuntimeError(
            f"Wrapped model '{self._model_name}' exhausted retries unexpectedly."
        )

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously invoke the wrapped model with retry/backoff."""
        if hasattr(self._model, "ainvoke"):
            for retry_index in range(self._max_retries + 1):
                try:
                    return await self._model.ainvoke(*args, **kwargs)
                except Exception as exc:
                    if retry_index >= self._max_retries or not _is_retryable_exception(exc):
                        raise
                    wait_seconds = self._compute_retry_delay(
                        exc,
                        retry_index=retry_index + 1,
                    )
                    self._log_retry(
                        exc,
                        retry_index=retry_index + 1,
                        wait_seconds=wait_seconds,
                    )
                    await asyncio.sleep(wait_seconds)
        elif hasattr(self._model, "invoke"):
            return await asyncio.to_thread(self.invoke, *args, **kwargs)
        else:
            raise AttributeError(
                f"Wrapped model '{self._model_name}' does not support ainvoke() or invoke()."
            )

        raise RuntimeError(
            f"Wrapped model '{self._model_name}' exhausted retries unexpectedly."
        )


def wrap_chat_model_with_retry(model: Any, *, model_name: str) -> RetryingChatModel:
    """Return a retrying wrapper around a registered chat model."""
    if isinstance(model, RetryingChatModel):
        return model
    return RetryingChatModel(model=model, model_name=model_name)


class UnifiedRegistry:
    """Unified Model Registry for model registration."""

    def __init__(self, factory: ModelFactory):
        self._factory = factory
        self._lc_registry = get_chat_model_registry()

    def register_model(self, service: str, name: str, **config_values):
        """Create and register a model with the LangChain registry."""
        try:
            model_instance = self._factory.create_model(service, name, **config_values)
            wrapped_model = wrap_chat_model_with_retry(
                model_instance,
                model_name=name,
            )

            self._lc_registry.register(
                name,
                wrapped_model,
                max_tokens=config_values.get("max_tokens"),
                hidden=config_values.get("hidden", False)
            )

            config_for_logging = {k: v for k, v in config_values.items() if k != "api_key"}
            carb.log_warn(f"Successfully registered model - service: {service}, name: {name}, config: {config_for_logging}")

        except (ValueError, ImportError) as e:
            carb.log_error(f"Failed to register model {name}: {str(e)}")
        except Exception as e:
            carb.log_error(f"Unexpected error registering model {name}: {str(e)}")

    def register_models(self, models: list[dict[str, Any]]):
        """Register multiple models in batch.

        Args:
            models: List of model configurations. Each item should be a dict with:
                - 'service': str - The service provider
                - 'name': str - The registry name for the model
                - 'model': str - The model name
                - Any additional configuration parameters

        Example:
            models = [
                {
                    'name': 'llama-3.1-70b-instruct',
                    'service': 'nvidia',
                    'model': 'meta/llama-3.1-70b-instruct',
                    'api_key': 'your-api-key',
                    'temperature': 0.1
                },
                {
                    'name': 'gpt-4o',
                    'service': 'openai',
                    'model': 'gpt-4o',
                    'api_key': 'your-api-key',
                    'temperature': 0.3
                }
            ]

        """
        carb.log_info(f"Starting batch registration of {len(models)} models")

        for model_config in models:
            try:
                # Validate required fields
                if 'service' not in model_config:
                    raise ValueError("'service' field is required")
                if 'name' not in model_config:
                    raise ValueError("'name' field is required")

                # Create a copy to avoid modifying the original
                config_copy = model_config.copy()

                # Extract service and name, rest are config parameters
                service = config_copy.pop('service')
                name = config_copy.pop('name')

                self.register_model(service, name, **config_copy)

            except Exception as e:
                name = model_config.get('name')
                carb.log_error(f"Failed to register model {name}: {str(e)}")

    def register_models_from_config(self, config_file_path: str):
        """Register models from a YAML configuration file.

        Args:
            config_file_path: Path to the YAML configuration file

        """
        with open(config_file_path, encoding='utf-8') as file:
            config_data = yaml.safe_load(file)

        self.register_models(config_data['models'])

        carb.log_info(f"Successfully loaded and registered {len(config_data['models'])} models from config file: {config_file_path}")

    def is_model_registered(self, name: str) -> bool:
        """Check if a model is registered."""
        return self._lc_registry.get_model(name) is not None

    def get_all_services(self) -> list[str]:
        """Get all available known service types as strings."""
        return self._factory.get_all_services()

    def list_available_models(self, service: str) -> list[str]:
        """List available models for a service."""
        return self._factory.get_available_models(service)

    def get_config_fields(self, service: str) -> dict[str, Any]:
        """Get configuration fields for a service."""
        return self._factory.get_config_fields(service)

    def get_field_defaults(self, service: str, name: str) -> dict[str, Any]:
        """Get default configuration for a specific model."""
        return self._factory.get_field_defaults(service, name)

# Global registry instance
_unified_registry = None

def get_unified_registry() -> UnifiedRegistry:
    """Get the global unified registry instance."""
    global _unified_registry
    if _unified_registry is None:
        factory = ModelFactory()
        _unified_registry = UnifiedRegistry(factory)
    return _unified_registry

def create_unified_registry(factory: ModelFactory) -> UnifiedRegistry:
    """Create a new unified registry instance with custom factory."""
    return UnifiedRegistry(factory=factory)