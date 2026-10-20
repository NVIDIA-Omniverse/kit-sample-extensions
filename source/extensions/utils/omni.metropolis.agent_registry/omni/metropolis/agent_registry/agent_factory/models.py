"""Supported models for each service."""

# Adapted from NVIDIA's internal lc-agent project (lc_agent_chat_models).

# Supported service types
SUPPORTED_SERVICES = ["nvidia", "openai", "anthropic", "azure_openai"]

OPENAI_MODELS = {
    "gpt-4o": (
        {
            "model": "chatgpt-4o-latest",
        },
        1024 * 128,
        False,
    ),
    "gpt-4o-mini": (
        {
            "model": "gpt-4o-mini",
        },
        1024 * 128,
        False,
    ),
    "o3-mini": (
        {
            "model": "o3-mini",
        },
        1024 * 128,
        False,
    ),
}

ANTHROPIC_MODELS = {
    "Sonnet-3.5.1": {"model": "claude-3-5-sonnet-20241022", "max_tokens": 4096},
    "Haiku-3.5": {"model": "claude-3-5-haiku-20241022", "max_tokens": 4096},
}

LLAMA_MODELS = {
    "meta/llama-3.1-70b-instruct": (
        {
            "model": "meta/llama-3.1-70b-instruct",
            "temperature": 0.1,
            "max_tokens": 4 * 1024, # maximum tokens to generate (output)
            "base_url": "https://integrate.api.nvidia.com/v1",
        },
        128 * 1024, # context size (input)
        False,
    ),
    "meta/llama-3.1-405b-instruct": (
        {
            "model": "meta/llama-3.1-405b-instruct",
            "temperature": 0.1,
            "max_tokens": 4 * 1024,
        },
        128 * 1024,
        False,
    ),
    # The following models need the `NV-Developer` org key
    "nvdev/meta/llama-3.1-70b-instruct": (
        {
            "model": "nvdev/meta/llama-3.1-70b-instruct",
            "max_tokens": 4 * 1024,
        },
        128 * 1024,
        False,
    ),
    "nvdev/nvidia/llama-3.1-405b-instruct": (
        {
            "model": "nvdev/nvidia/llama-3.1-405b-instruct",
            "max_tokens": 4 * 1024,
        },
        128 * 1024,
        False,
    ),
    "nvdev/meta/llama-3.2-90b-vision-instruct": (
        {
            "model": "nvdev/meta/llama-3.2-90b-vision-instruct",
            "max_tokens": 4 * 1024,
            "base_url": "https://ai.api.nvidia.com/v1/gr/nvdev/meta/llama-3.2-90b-vision-instruct/chat/completions",
        },
        128 * 1024,
        False,
    ),

}

NEMOTRON_MODELS = {
    "NVINT-NEMOTRON4340BI": {"model": "nvidia/nemotron-4-340b-instruct", "temperature": 0.1, "max_tokens": 1024},
    # This one is not completion and doesn't support streaming.
    # "NVINT-NEMOTRON4340BR": {"model": "nvidia/nemotron-4-340b-reward", "temperature": 0.1, "max_tokens": 1024},
}

AZURE_MODELS = {
    "gpt-4-turbo": (
        {
            "azure_deployment": "gpt-4-turbo",
            "api_version": "2024-02-15-preview",
        },
        8192,
        False,
    ),
    "gpt-35-turbo": (
        {
            "azure_deployment": "gpt-35-turbo",
            "api_version": "2024-02-15-preview",
        },
        4096,
        False,
    ),
}