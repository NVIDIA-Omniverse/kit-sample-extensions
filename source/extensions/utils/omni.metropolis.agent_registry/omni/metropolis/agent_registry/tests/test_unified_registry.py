"""Tests for the unified registry module."""

from unittest.mock import AsyncMock, Mock, patch

import omni.kit.test
from omni.metropolis.agent_registry.agent_factory.model_factory import ModelFactory
from omni.metropolis.agent_registry.registry.unified_registry import (
    RetryingChatModel,
    UnifiedRegistry,
    create_unified_registry,
    get_unified_registry,
)


class TestUnifiedRegistry(omni.kit.test.AsyncTestCase):
    """Test suite for UnifiedRegistry class."""

    async def setUp(self):
        """Set up test environment."""
        self.mock_factory = Mock(spec=ModelFactory)
        self.mock_lc_registry = Mock()
        self.registry = UnifiedRegistry(factory=self.mock_factory)
        self.registry._lc_registry = self.mock_lc_registry

    async def tearDown(self):
        """Clean up test environment."""
        pass

    async def test_registry_initialization(self):
        """Test that registry initializes correctly."""
        self.assertIsNotNone(self.registry)
        self.assertEqual(self.registry._factory, self.mock_factory)
        self.assertEqual(self.registry._lc_registry, self.mock_lc_registry)

    async def test_register_model_success(self):
        """Test successful model registration."""
        # Mock the factory to return a model instance
        mock_model_instance = Mock()
        self.mock_factory.create_model.return_value = mock_model_instance

        # Mock the LC registry
        self.mock_lc_registry.get_model.return_value = None  # Model not already registered

        # Test registration
        self.registry.register_model(
            "openai",
            "test-model",
            api_key="test-key",
            max_tokens=2048,
            hidden=False
        )

        # Verify factory was called correctly
        self.mock_factory.create_model.assert_called_once_with(
            "openai", "test-model",
            api_key="test-key", max_tokens=2048, hidden=False
        )

        # Verify LC registry was called correctly
        self.mock_lc_registry.register.assert_called_once()
        register_args, register_kwargs = self.mock_lc_registry.register.call_args
        self.assertEqual(register_args[0], "test-model")
        self.assertIsInstance(register_args[1], RetryingChatModel)
        self.assertIs(register_args[1].base_model, mock_model_instance)
        self.assertEqual(
            register_kwargs,
            {"max_tokens": 2048, "hidden": False},
        )

    async def test_register_model_already_registered(self):
        """Test model registration when model is already registered."""
        # Mock the factory to return a model instance
        mock_model_instance = Mock()
        self.mock_factory.create_model.return_value = mock_model_instance

        # Mock the LC registry to return an existing model
        self.mock_lc_registry.get_model.return_value = Mock()

        # Test registration
        self.registry.register_model(
            "openai",
            "test-model",
            api_key="test-key"
        )

        # Verify register was called
        self.mock_lc_registry.register.assert_called_once()

    async def test_register_model_factory_error(self):
        """Test model registration when factory fails."""
        # Mock the factory to raise an error
        self.mock_factory.create_model.side_effect = ValueError("Invalid model")

        # Test registration should not raise an exception
        self.registry.register_model(
            "openai",
            "test-model",
            api_key="test-key"
        )

        # Verify LC registry was not called
        self.mock_lc_registry.register.assert_not_called()

    async def test_retrying_chat_model_retries_async_rate_limits(self):
        """Test async retry/backoff for transient provider throttling."""

        class _FlakyModel:
            def __init__(self) -> None:
                self.calls = 0

            async def ainvoke(self, *_args, **_kwargs):
                self.calls += 1
                if self.calls < 3:
                    raise RuntimeError("[429] Too Many Requests")
                return {"status": "ok"}

        flaky_model = _FlakyModel()
        # Pin the delay alongside the retry count and jitter so the assertions below cover the
        # doubling behavior itself rather than whatever the module defaults are tuned to.
        wrapped_model = RetryingChatModel(
            flaky_model,
            model_name="test-model",
            max_retries=3,
            initial_retry_delay_seconds=1.0,
            retry_jitter_factor=0.0,
        )

        with patch(
            "omni.metropolis.agent_registry.registry.unified_registry.asyncio.sleep",
            new=AsyncMock(),
        ) as mock_sleep:
            result = await wrapped_model.ainvoke(["message"])

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(flaky_model.calls, 3)
        self.assertEqual(mock_sleep.await_count, 2)
        mock_sleep.assert_any_await(1.0)
        mock_sleep.assert_any_await(2.0)



    async def test_is_model_registered_true(self):
        """Test checking if model is registered when it exists."""
        # Mock the LC registry to return a model
        self.mock_lc_registry.get_model.return_value = Mock()

        # Test check
        result = self.registry.is_model_registered("test-model")

        # Verify result
        self.assertTrue(result)
        self.mock_lc_registry.get_model.assert_called_once_with("test-model")

    async def test_is_model_registered_false(self):
        """Test checking if model is registered when it doesn't exist."""
        # Mock the LC registry to return None
        self.mock_lc_registry.get_model.return_value = None

        # Test check
        result = self.registry.is_model_registered("test-model")

        # Verify result
        self.assertFalse(result)
        self.mock_lc_registry.get_model.assert_called_once_with("test-model")

    async def test_get_all_services(self):
        """Test getting all available services."""
        expected_services = ["openai", "anthropic"]
        self.mock_factory.get_all_services.return_value = expected_services

        # Test getting services
        result = self.registry.get_all_services()

        # Verify result
        self.assertEqual(result, expected_services)
        self.mock_factory.get_all_services.assert_called_once()

    async def test_list_available_models(self):
        """Test listing available models for a service."""
        mock_models = ["model1", "model2"]
        self.mock_factory.get_available_models.return_value = mock_models

        # Test listing models
        result = self.registry.list_available_models("openai")

        # Verify result
        self.assertEqual(result, ["model1", "model2"])
        self.mock_factory.get_available_models.assert_called_once_with("openai")

    async def test_get_config_fields(self):
        """Test getting configuration fields for a service."""
        expected_fields = {"api_key": "string", "model": "string"}
        self.mock_factory.get_config_fields.return_value = expected_fields

        # Test getting config fields
        result = self.registry.get_config_fields("openai")

        # Verify result
        self.assertEqual(result, expected_fields)
        self.mock_factory.get_config_fields.assert_called_once_with("openai")

    async def test_get_field_defaults(self):
        """Test getting field defaults."""
        expected_defaults = {"temperature": 0.7, "max_tokens": 4096}
        self.mock_factory.get_field_defaults.return_value = expected_defaults

        # Test getting field defaults
        result = self.registry.get_field_defaults("openai", "test-model")

        # Verify result
        self.assertEqual(result, expected_defaults)
        self.mock_factory.get_field_defaults.assert_called_once_with("openai", "test-model")

    async def test_register_models_success(self):
        """Test successful batch model registration."""
        # Mock the factory to return model instances
        mock_model1 = Mock()
        mock_model2 = Mock()
        self.mock_factory.create_model.side_effect = [mock_model1, mock_model2]

        # Mock the LC registry
        self.mock_lc_registry.get_model.return_value = None  # Models not already registered

        # Test batch registration
        models = [
            {
                "service": "openai",
                "name": "gpt-4o",
                "api_key": "test-key-1",
                "temperature": 0.3
            },
            {
                "service": "anthropic",
                "name": "claude",
                "api_key": "test-key-2",
                "temperature": 0.1
            }
        ]

        self.registry.register_models(models)

        # Verify factory was called for both models
        self.assertEqual(self.mock_factory.create_model.call_count, 2)
        self.mock_factory.create_model.assert_any_call(
            "openai", "gpt-4o", api_key="test-key-1", temperature=0.3
        )
        self.mock_factory.create_model.assert_any_call(
            "anthropic", "claude", api_key="test-key-2", temperature=0.1
        )

        # Verify LC registry was called for both models
        self.assertEqual(self.mock_lc_registry.register.call_count, 2)

    async def test_register_models_with_errors(self):
        """Test batch registration with some models failing."""
        # Mock the factory to fail for the second model
        mock_model1 = Mock()
        self.mock_factory.create_model.side_effect = [mock_model1, ValueError("Invalid model")]

        # Mock the LC registry
        self.mock_lc_registry.get_model.return_value = None

        # Test batch registration with mixed success/failure
        models = [
            {
                "service": "openai",
                "name": "valid-model",
                "api_key": "test-key"
            },
            {
                "service": "openai",
                "name": "invalid-model",
                "api_key": "bad-key"
            }
        ]

        # Should not raise an exception
        self.registry.register_models(models)

        # Verify factory was called for both models
        self.assertEqual(self.mock_factory.create_model.call_count, 2)

        # Verify LC registry was only called once (for the successful model)
        self.mock_lc_registry.register.assert_called_once()

    async def test_register_models_validation_errors(self):
        """Test batch registration with validation errors."""
        # Mock the factory to raise ValueError for missing 'model' field (simulating real behavior)
        self.mock_factory.create_model.side_effect = ValueError("'model' field is required.")

        # Test with missing required fields
        models = [
            {
                "service": "openai",
                # Missing name - fails validation in register_models
                "api_key": "test-key"
            },
            {
                # Missing service - fails validation in register_models
                "name": "test-model",
                "api_key": "test-key"
            },
            {
                "service": "custom-service",  # Custom service but missing required 'model' field
                "name": "test-model",        # Passes register_models validation but fails in factory
                "api_key": "test-key"
            }
        ]

        # Should not raise an exception (errors are logged, not raised)
        self.registry.register_models(models)

        # First two fail validation in register_models (missing name/service)
        # Third passes register_models validation but factory raises ValueError for missing 'model'
        self.assertEqual(self.mock_factory.create_model.call_count, 1)
        self.mock_factory.create_model.assert_called_with('custom-service', 'test-model', api_key='test-key')

        # LC registry should not be called since factory raised an error
        self.mock_lc_registry.register.assert_not_called()

    @patch('builtins.open')
    @patch('yaml.safe_load')
    async def test_register_models_from_config_success(self, mock_yaml_load, mock_open):
        """Test successful model registration from config file."""
        # Mock YAML content
        mock_config_data = {
            'models': [
                {
                    'service': 'openai',
                    'name': 'test-model-1',
                    'model': 'gpt-4',
                    'api_key': 'test-key-1'
                },
                {
                    'service': 'nvidia',
                    'name': 'test-model-2',
                    'model': 'llama-3.1-70b',
                    'api_key': 'test-key-2'
                }
            ]
        }
        mock_yaml_load.return_value = mock_config_data

        # Mock the factory to return model instances
        mock_model_instance = Mock()
        self.mock_factory.create_model.return_value = mock_model_instance

        # Test config file registration
        config_file_path = "/test/config.yaml"
        self.registry.register_models_from_config(config_file_path)

        # Verify file was opened
        mock_open.assert_called_once_with(config_file_path, encoding='utf-8')

        # Verify YAML was loaded
        mock_yaml_load.assert_called_once()

        # Verify models were registered (2 models)
        self.assertEqual(self.mock_factory.create_model.call_count, 2)
        self.assertEqual(self.mock_lc_registry.register.call_count, 2)




class TestUnifiedRegistryFunctions(omni.kit.test.AsyncTestCase):
    """Test suite for unified registry functions."""

    async def setUp(self):
        """Set up test environment."""
        pass

    async def tearDown(self):
        """Clean up test environment."""
        pass

    @patch('omni.metropolis.agent_registry.registry.unified_registry._unified_registry', None)
    @patch('omni.metropolis.agent_registry.registry.unified_registry.ModelFactory')
    async def test_get_unified_registry_creates_instance(self, mock_model_factory_class):
        """Test that get_unified_registry creates a new instance when none exists."""
        # Mock the ModelFactory
        mock_factory = Mock()
        mock_model_factory_class.return_value = mock_factory

        # Test getting registry
        registry = get_unified_registry()

        # Verify registry was created
        self.assertIsNotNone(registry)
        self.assertIsInstance(registry, UnifiedRegistry)
        mock_model_factory_class.assert_called_once()

    async def test_get_unified_registry_returns_existing(self):
        """Test that get_unified_registry returns existing instance."""
        # Set up existing registry
        existing_registry = Mock(spec=UnifiedRegistry)

        # Use patch to directly set _unified_registry to our existing registry
        with patch('omni.metropolis.agent_registry.registry.unified_registry._unified_registry', existing_registry):
            # Test getting registry
            registry = get_unified_registry()

            # Verify existing registry was returned
            self.assertEqual(registry, existing_registry)

    async def test_create_unified_registry(self):
        """Test creating a new unified registry with custom factory."""
        # Create a mock factory
        mock_factory = Mock(spec=ModelFactory)

        # Test creating registry
        registry = create_unified_registry(mock_factory)

        # Verify registry was created correctly
        self.assertIsNotNone(registry)
        self.assertIsInstance(registry, UnifiedRegistry)
        self.assertEqual(registry._factory, mock_factory)

    @patch('omni.metropolis.agent_registry.registry.unified_registry._unified_registry', None)
    @patch('omni.metropolis.agent_registry.registry.unified_registry.ModelFactory')
    async def test_get_unified_registry_integration(self, mock_model_factory_class):
        """Test integration of get_unified_registry with actual factory."""
        # Mock the ModelFactory and its dependencies
        mock_factory = Mock(spec=ModelFactory)
        mock_model_factory_class.return_value = mock_factory

        # Mock the LC registry
        mock_lc_registry = Mock()
        with patch('omni.metropolis.agent_registry.registry.unified_registry.get_chat_model_registry') as mock_get_lc_registry:
            mock_get_lc_registry.return_value = mock_lc_registry

            # Test getting registry
            registry = get_unified_registry()

            # Verify registry was created with correct dependencies
            self.assertIsNotNone(registry)
            self.assertEqual(registry._factory, mock_factory)
            self.assertEqual(registry._lc_registry, mock_lc_registry)