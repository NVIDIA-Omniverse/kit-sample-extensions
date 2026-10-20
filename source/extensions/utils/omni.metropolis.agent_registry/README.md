# Omni Metropolis Agent Registry

A unified model registry system for managing and configuring various AI/LLM models within the Omniverse Metropolis simulation environment.

## 🌟 Features

- **Unified API**: Single interface for registering and managing multiple model types
- **Multi-Provider Support**: OpenAI, Azure OpenAI, Anthropic, NVIDIA, and custom models
- **Flexible Authentication**: API keys, OAuth, credential files, and environment variables
- **Model-Specific Optimizations**: Custom adapters for Llama, Nemotron, and other specialized models
- **Configuration-Driven**: Support for JSON/YAML configuration files
- **Factory Pattern**: Extensible architecture for adding new model types

## 📋 Supported Models

### OpenAI Models
- GPT-4o, GPT-4o-mini, O3-mini
- Custom OpenAI-compatible endpoints

### Azure OpenAI
- Azure-hosted OpenAI models
- LLM Gateway integration
- Credential file authentication

### Anthropic
- Claude 3.5 Sonnet, Claude 3.5 Haiku
- Claude 3.7 Sonnet (with thinking mode)

### NVIDIA Models
- Llama 3.1 (70B, 405B variants)
- Llama 4 (Maverick, Scout variants)
- Nemotron 4 (340B Instruct)
- Custom NVIDIA API endpoints

### Testing & Development
- Fake models for testing and development

## 🚀 Quick Start

### Basic Usage

```python
from omni.metropolis.agent_registry.agent_factory.unified_model_registry import (
    get_unified_registry, ModelConfig, ModelType, create_openai_config
)

# Get the global registry
registry = get_unified_registry()

# Register a simple OpenAI model
openai_model = create_openai_config(
    name="gpt-4o",
    model_name="gpt-4o",
    max_tokens=4096,
    temperature=0.1
)
registry.register_model(openai_model)
```

### Using Existing Registration Functions

```python
# Register Llama models
from omni.metropolis.agent_registry.llm_adapters.register_llama_model import register_llama_model

register_llama_model(
    model_names=["meta/llama-3.1-70b-instruct"],
    api_key="your-nvidia-api-key"
)

# Register Nemotron models
from omni.metropolis.agent_registry.llm_adapters.register_nemotron_models import register_nemotron_models

register_nemotron_models(
    model_names=["NVINT-NEMOTRON4340BI"],
    api_key="your-nvidia-api-key"
)
```

## 🏗 Architecture

### Core Components

```
agent_registry/
├── agent_factory/
│   └── unified_model_registry.py    # Main registry and factory classes
├── llm_adapters/
│   ├── azure_openai_llm_gateway.py  # Azure LLM Gateway integration
│   ├── register_llama_model.py      # Llama model registration
│   └── register_nemotron_models.py  # Nemotron model registration
└── test/
    └── unified_examples.py          # Usage examples
```

### Factory Pattern

The system uses a factory pattern with specialized factories for different model types:

- **OpenAIModelFactory**: Handles OpenAI, Llama, and Nemotron models
- **AzureOpenAIModelFactory**: Manages Azure OpenAI and LLM Gateway models
- **AnthropicModelFactory**: Anthropic Claude models
- **NVIDIAModelFactory**: Direct NVIDIA API models
- **FakeModelFactory**: Testing and development models

## ⚙️ Configuration

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# NVIDIA
export NVIDIA_API_KEY="nvapi-..."
export NVIDIA_FUNC_ID="your-function-id"  # For custom endpoints
```

### Model Configuration

```python
# Advanced model configuration
azure_model = ModelConfig(
    name="azure-gpt4",
    model_type=ModelType.AZURE_OPENAI,
    model_name="gpt-4-turbo",
    azure_endpoint="https://your-endpoint.openai.azure.com/",
    azure_deployment="gpt-4-turbo",
    api_version="2024-02-15-preview",
    max_tokens=8192,
    temperature=0.1,
    extra_params={"streaming": True}
)
```

### Authentication Methods

#### API Key Authentication
```python
config = ModelConfig(
    name="my-model",
    model_type=ModelType.OPENAI,
    model_name="gpt-4o",
    api_key="sk-...",  # Direct API key
    # OR
    api_key_env_var="CUSTOM_API_KEY"  # Environment variable
)
```

#### Credential File Authentication
```python
config = ModelConfig(
    name="azure-model",
    model_type=ModelType.AZURE_LLM_GATEWAY,
    model_name="gpt-4-turbo",
    credential_file_url="https://your-domain.com/creds.json",
    credential_fields=["token_url", "client_id", "client_secret", "scope"]
)
```

## 📚 Examples

### Register Multiple Models

```python
from omni.metropolis.agent_registry.agent_factory.unified_model_registry import *

registry = get_unified_registry()

models = [
    create_openai_config("gpt-4o", "gpt-4o", max_tokens=128*1024),
    create_anthropic_config("claude-sonnet", "claude-3-5-sonnet-20241022", max_tokens=4096),
    create_llama_config("llama-70b", "meta/llama-3.1-70b-instruct", max_tokens=4*1024)
]

registry.register_models(models)
```

### Selective Model Registration

```python
# Register only specific models
registry.register_models(models, model_names=["gpt-4o", "claude-sonnet"])
```

### Configuration from File

```python
import json

# Load from JSON configuration
with open("model_config.json") as f:
    config_data = json.load(f)

models = []
for model_data in config_data["models"]:
    model_type = ModelType(model_data.pop("model_type"))
    config = ModelConfig(model_type=model_type, **model_data)
    models.append(config)

registry.register_models(models)
```

Example `model_config.json`:
```json
{
  "models": [
    {
      "name": "production-gpt4",
      "model_type": "openai",
      "model_name": "gpt-4o",
      "max_tokens": 4096,
      "temperature": 0.1,
      "api_key_env_var": "OPENAI_API_KEY"
    },
    {
      "name": "production-claude",
      "model_type": "anthropic", 
      "model_name": "claude-3-5-sonnet-20241022",
      "max_tokens": 4096,
      "api_key_env_var": "ANTHROPIC_API_KEY"
    }
  ]
}
```

## 🔧 Custom Model Adapters

### PatchedChatOpenAI

Custom OpenAI adapter that handles `max_tokens` vs `max_completion_tokens` compatibility:

```python
from omni.metropolis.agent_registry.llm_adapters.register_llama_model import PatchedChatOpenAI

model = PatchedChatOpenAI(
    model="meta/llama-3.1-70b-instruct",
    api_key="nvapi-...",
    base_url="https://integrate.api.nvidia.com/v1",
    max_tokens=4096
)
```

### ChatNemotron

Specialized adapter for NVIDIA Nemotron models:

```python
from omni.metropolis.agent_registry.llm_adapters.register_nemotron_models import ChatNemotron

model = ChatNemotron(
    model="nvidia/nemotron-4-340b-instruct",
    api_key="nvapi-...",
    base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.1,
    max_tokens=1024
)
```

## 🛠 Installation & Setup

### Prerequisites

```bash
pip install langchain-openai langchain-anthropic langchain-nvidia-ai-endpoints langchain-community
```

### Extension Setup

1. Place the extension in your Omniverse extensions directory
2. Set up environment variables for your API keys
3. Import and use the registry in your code

### Dependencies

- `lc_agent`: Core agent framework
- `langchain-openai`: OpenAI and Azure OpenAI support
- `langchain-anthropic`: Anthropic Claude support  
- `langchain-nvidia-ai-endpoints`: NVIDIA model support
- `langchain-community`: Community models and fake models

## 🧪 Testing

```python
# Use fake models for testing
fake_config = ModelConfig(
    name="test-model",
    model_type=ModelType.FAKE,
    model_name="fake",
    extra_params={"responses": ["Test response 1", "Test response 2"]}
)

registry.register_model(fake_config)
```

## 🤝 Contributing

1. Follow the existing factory pattern for new model types
2. Add appropriate error handling and validation
3. Include examples in the `test/unified_examples.py` file
4. Update this README with new features

## 📄 License

This project is part of the NVIDIA Omniverse Metropolis simulation framework.

## 🐛 Troubleshooting

### Common Issues

**Import Errors**: Ensure all required langchain packages are installed
```bash
pip install langchain-openai langchain-anthropic langchain-nvidia-ai-endpoints
```

**Authentication Failures**: Verify API keys and credentials are properly set
```python
import os
print(os.environ.get("OPENAI_API_KEY"))  # Should not be None
```

**Model Registration Failures**: Check model names and configuration parameters
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📞 Support

For issues and questions related to this agent registry system, please refer to the Omniverse Metropolis documentation or contact the development team. 