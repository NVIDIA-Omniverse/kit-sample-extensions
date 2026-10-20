"""Tests for the model factory module."""

import omni.kit.test
from omni.metropolis.agent_registry.agent_factory.model_factory import ModelFactory
from omni.metropolis.agent_registry.agent_factory.models import SUPPORTED_SERVICES


class TestModelFactory(omni.kit.test.AsyncTestCase):
    """Test suite for ModelFactory class."""

    async def setUp(self):
        """Set up test environment."""
        self.factory = ModelFactory()

    async def tearDown(self):
        """Clean up test environment."""
        pass

    async def test_factory_initialization(self):
        """Test that the factory initializes correctly."""
        self.assertIsNotNone(self.factory)
        self.assertIsInstance(self.factory._service_settings, dict)
        self.assertIsInstance(self.factory._langchain_classes, dict)

    async def test_get_all_services(self):
        """Test that all supported service types are returned."""
        services = self.factory.get_all_services()
        self.assertIsInstance(services, list)

        # Check that all expected service types are present
        expected_services = [
            "openai",
            "anthropic",
            "nvidia",
            "azure_openai"
        ]

        for expected_service in expected_services:
            self.assertIn(expected_service, services)

    async def test_service_settings_initialized(self):
        """Test that service settings are properly initialized."""
        # Check that all service types have settings
        for service_type in SUPPORTED_SERVICES:
            self.assertIn(service_type, self.factory._service_settings)

        # Check that each service setting has required attributes
        for service_type, setting in self.factory._service_settings.items():
            self.assertIsNotNone(setting.models)
            self.assertIsNotNone(setting.config_class)
            self.assertIsNotNone(setting.langchain_class)

    async def test_get_available_models(self):
        """Test getting available models for a service."""
        # Test OpenAI models
        openai_models = self.factory.get_available_models("openai")
        self.assertIsInstance(openai_models, list)
        self.assertGreater(len(openai_models), 0)

        # Check that models are strings
        for model_name in openai_models:
            self.assertIsInstance(model_name, str)
            self.assertGreater(len(model_name), 0)

    async def test_get_config_fields(self):
        """Test getting configuration fields for a service."""
        # Test OpenAI config fields
        openai_fields = self.factory.get_config_fields("openai")
        self.assertIsInstance(openai_fields, dict)
        self.assertGreater(len(openai_fields), 0)

        # Check that required fields are present
        self.assertIn('api_key', openai_fields)
        self.assertIn('model', openai_fields)