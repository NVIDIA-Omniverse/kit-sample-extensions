"""Model Registry Panel."""

from typing import Any, Union, get_args, get_origin

import carb
import omni.ui as ui
from omni.kit.widget.settings import SettingType, create_setting_widget
from omni.metropolis.utils.ui_util import MinimalStringListModel
from pydantic.fields import FieldInfo

from ..registry import get_unified_registry
from ..settings import ModelRegistrySetting


class ModelRegistryPanel:
    """Model Registry Panel for UI Interaction with the Model Registry."""

    def __init__(self):
        self._frame = None
        self._service_dropdown_model = None
        self._model_dropdown_model = None
        self._config_container = None
        self._config_models = {}
        self._current_service: str = None
        self._current_name = None
        self._services = []
        self._names = []

        self._config_file_path_model = None
        self._config_file_status_label = None
        self._register_custom_model = False
        self.unified_registry = get_unified_registry()

    def _build_ui(self) -> None:
        """Build the complete UI."""
        with self._frame:
            with ui.VStack(spacing=10):
                ui.Spacer(height=5)

                # API Key Settings Section
                with ui.VStack(spacing=10):
                    with ui.HStack(height=20):
                        ui.Spacer(width=20)
                        title_label = ui.Label("API Key Settings", height=ui.Percent(1))
                        title_label.set_style({"font_size": 16, "color": 0xFFFFFFFF, "font_style": "bold"})

                    # Build API key fields
                    api_key_settings = ModelRegistrySetting.get_all_api_key_settings()
                    for service, setting_name in api_key_settings.items():
                        self._build_single_api_key_field(service, setting_name)

                # Separator
                ui.Separator(height=2)
                ui.Spacer(height=5)

                # Config File Registration Section
                with ui.VStack(spacing=10):
                    # Section Title
                    with ui.HStack(height=20):
                        ui.Spacer(width=20)
                        title_label = ui.Label("Registration from Config File", height=ui.Percent(1))
                        title_label.set_style({"font_size": 16, "color": 0xFFFFFFFF, "font_style": "bold"})

                    # File picker row
                    with ui.HStack(height=25, spacing=5, alignment=ui.Alignment.CENTER):
                        ui.Spacer(width=20)
                        ui.Label("Config File", width=150, height=ui.Percent(1))

                        with ui.HStack(alignment=ui.Alignment.LEFT_CENTER, spacing=5):
                            # File path field
                            self._config_file_path_model = ui.SimpleStringModel("")
                            config_file_field = ui.StringField(
                                self._config_file_path_model,
                                width=300,
                                height=ui.Percent(1)
                            )
                            config_file_field.set_tooltip("Path to the config file (can be typed manually or selected via Browse)")

                            # Browse button
                            browse_button = ui.Button("Browse", width=80, height=ui.Percent(1))
                            browse_button.set_clicked_fn(self._on_browse_config_file)
                            browse_button.set_tooltip("Browse for YAML config file")

                    # Register from config button and status
                    with ui.HStack(height=15, spacing=10, alignment=ui.Alignment.CENTER):
                        # Register button
                        register_config_button = ui.Button(
                            "Register from Config File", width=250, alignment=ui.Alignment.CENTER
                        )
                        register_config_button.set_clicked_fn(self._on_register_from_config_clicked)
                        register_config_button.set_tooltip("Register all models from the selected config file")

                        # Status label
                        self._config_file_status_label = ui.Label("", width=300, height=ui.Percent(1))
                        self._config_file_status_label.set_style({"color": 0xFFAAAAAA, "font_size": 11})

                # Separator
                ui.Separator(height=2)
                ui.Spacer(height=5)

                # Individual Model Registration Section
                with ui.VStack(spacing=10):
                    # Section Title
                    with ui.HStack(height=20):
                        ui.Spacer(width=20)
                        title_label = ui.Label("Individual Model Registration", height=ui.Percent(1))
                        title_label.set_style({"font_size": 16, "color": 0xFFFFFFFF, "font_style": "bold"})

                    # Service Selection
                    self._build_service_selection()

                    # Model Selection
                    self._build_model_selection()

                    # Configuration Fields
                    self._build_config_container()

                    # Register Button
                    with ui.HStack(height=15, spacing=5, alignment=ui.Alignment.CENTER):
                        register_button = ui.Button(
                            "Register Model", width=250, alignment=ui.Alignment.CENTER
                        )
                        register_button.set_clicked_fn(self._on_register_clicked)

    def build_ui_frame(self) -> None:
        """Build the UI frame with collapsible frame design."""
        if self._frame is None:
            self._frame = ui.CollapsableFrame(
                title="Model Registry",
                height=20,
                collapsed=False,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
            )
            self._build_ui()


    def _build_single_api_key_field(self, _service: str, setting_name: str) -> None:
        """Build a single API key field for a service."""
        with ui.HStack(height=25, spacing=5, alignment=ui.Alignment.CENTER):
            ui.Spacer(width=20)

            label_text = setting_name.replace("_", " ")
            ui.Label(label_text, width=150, height=ui.Percent(1))

            with ui.HStack(alignment=ui.Alignment.LEFT_CENTER):
                setting_path = ModelRegistrySetting.get_setting_path(setting_name)
                create_setting_widget(
                    setting_path,
                    SettingType.STRING,
                    hard_range=False,
                    width=400,
                    height=ui.Percent(1),
                )

    #########################################################################################
    # Individual Model Registration Section
    #########################################################################################

    def _build_service_selection(self):
        """Build service selection dropdown."""
        with ui.HStack(height=25, spacing=5, alignment=ui.Alignment.CENTER):
            ui.Spacer(width=20)
            service_label = ui.Label("Service", width=150, height=ui.Percent(1))
            service_label.set_tooltip("Select the model service")

            with ui.HStack(alignment=ui.Alignment.LEFT_CENTER):
                try:
                    self._services = self.unified_registry.get_all_services()
                    if self._services:
                        # Add "Select a Service" as the first option
                        services_with_options = ["Select a Service"] + self._services
                        self._service_dropdown_model = MinimalStringListModel(services_with_options)
                        ui.ComboBox(self._service_dropdown_model, width=400, height=ui.Percent(1))
                        self._service_dropdown_model.add_item_changed_fn(self._on_service_changed)
                    else:
                        ui.Label("No services available", width=400, height=ui.Percent(1))
                except Exception as e:
                    carb.log_error(f"Failed to load services: {e}")
                    ui.Label("Error loading services", width=400, height=ui.Percent(1))

    def _build_model_selection(self):
        """Build model selection dropdown."""
        with ui.HStack(height=25, spacing=5, alignment=ui.Alignment.CENTER):
            ui.Spacer(width=20)
            model_label = ui.Label("Model", width=150, height=ui.Percent(1))
            model_label.set_tooltip("Select the model to register")

            with ui.HStack(alignment=ui.Alignment.LEFT_CENTER):
                self._model_dropdown_model = MinimalStringListModel(["Select a service first"])
                ui.ComboBox(self._model_dropdown_model, width=400, height=ui.Percent(1))
                self._model_dropdown_model.add_item_changed_fn(self._on_model_changed)

    def _build_config_container(self):
        """Build container for configuration fields."""
        with ui.HStack(spacing=5):
            ui.Spacer(width=20)
            self._config_container = ui.VStack(spacing=5)
            ui.Spacer(width=20)

    def _on_service_changed(self, _model, *_args):
        """Handle service selection change."""
        if not self._service_dropdown_model:
            return

        selected_index = self._service_dropdown_model.get_item_value_model().get_value_as_int()

        if selected_index == 0:
            # "Select a Service" option selected
            self._current_service = None
            self._current_name = None
            self._register_custom_model = False

            # Reset model dropdown
            if self._model_dropdown_model:
                self._model_dropdown_model.set_item_children(["Select a service first"])
                self._model_dropdown_model.get_item_value_model().set_value(0)
            self._clear_config_fields()
        elif 1 <= selected_index <= len(self._services):
            service_index = selected_index - 1
            self._current_service = self._services[service_index]
            # Reset model selection and custom model mode when service changes
            self._current_name = None
            self._register_custom_model = False
            self._update_model_dropdown()
            self._build_config_fields()

    def _on_model_changed(self, _model, *_args):
        """Handle model selection change."""
        if not self._model_dropdown_model:
            return

        selected_index = self._model_dropdown_model.get_item_value_model().get_value_as_int()

        # Check if service is selected before allowing model selection
        if not self._current_service:
            # Reset to the first option and show error for any dropdown interaction
            self._model_dropdown_model.get_item_value_model().set_value(0)
            carb.log_warn("Please select a service before selecting a model")
            return

        if selected_index == 0:
            # "Select a Model" option selected
            self._current_name = None
            self._register_custom_model = False
        elif 1 <= selected_index <= len(self._names):
            # Actual model selected (adjust index for "Select a Model" option)
            model_index = selected_index - 1

            # Get the model name
            self._current_name = self._names[model_index]
            self._register_custom_model = False
        elif selected_index == len(self._names) + 1:
            # register custom model option selected
            self._current_name = None
            self._register_custom_model = True
        self._build_config_fields()

    def _update_model_dropdown(self):
        """Update model dropdown based on selected service."""
        if not self._current_service:
            return

        try:
            self._names = self.unified_registry.list_available_models(self._current_service)
            if self._names:
                # Add "Select a Model" as first option, models, then "Register Custom Model"
                dropdown_options = ["Select a Model"] + self._names + ["(Register Custom Model)"]
                self._model_dropdown_model.set_item_children(dropdown_options)
                self._model_dropdown_model.get_item_value_model().set_value(0)
            else:
                self._model_dropdown_model.set_item_children(["Select a Model", "(Register Custom Model)"])
                self._model_dropdown_model.get_item_value_model().set_value(0)
        except Exception as e:
            carb.log_error(f"Failed to load models for service {self._current_service}: {e}")
            self._model_dropdown_model.set_item_children(["Error loading models"])
            self._model_dropdown_model.get_item_value_model().set_value(0)

    def _clear_config_fields(self):
        """Clear all configuration fields."""
        if self._config_container:
            self._config_container.clear()
            self._config_models.clear()

    def _build_config_fields(self):
        """Build configuration fields based on the selected service and model."""
        if not self._current_service:
            return

        self._clear_config_fields()

        try:
            config_fields = self.unified_registry.get_config_fields(self._current_service)
            defaults = self.unified_registry.get_field_defaults(self._current_service, self._current_name)

            with self._config_container:
                # Title for configuration section
                with ui.HStack(height=20):
                    title = ui.Label("Configuration", width=600, height=ui.Percent(1))
                    title.set_style({"font_size": 14, "color": 0xFFFFFFFF})

                ui.Spacer(height=5)

                # Build fields based on Pydantic schema
                for field_name, field_info in config_fields.items():
                    self._build_config_field(field_name, field_info, defaults)

        except Exception as e:
            carb.log_error(f"Error building config fields: {e}")
            with self._config_container:
                ui.Label(f"Error: {str(e)}", width=600, height=ui.Percent(1))

    def _get_type_display(self, field_type: Any) -> str:
        """Get display string for field type."""
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            type_names = []
            for arg in args:
                if arg is type(None):
                    type_names.append("None")
                else:
                    type_names.append(getattr(arg, "__name__", str(arg)))
            return " or ".join(type_names)
        return getattr(field_type, "__name__", str(field_type))

    def _augment_field_default_value(self, field_name: str, field_default: Any) -> str:
        """Augment the default value for a field by adding the current name and/or API key."""
        if field_name == "name" and self._current_name and not self._register_custom_model:
            return self._current_name
        elif field_name == "api_key" and self._current_service:
            carb_api_key = ModelRegistrySetting.get_api_key_for_service(self._current_service)
            if carb_api_key:
                return carb_api_key
            else:
                with ui.HStack(height=20, spacing=5, alignment=ui.Alignment.CENTER):
                    ui.Spacer(width=20)
                    label = ui.Label(
                        f"No API key found in carb settings for {self._current_service}. "
                        "Please ensure the API key is set if it is required.",
                        width=400,
                        height=ui.Percent(1)
                    )
                    label.set_style({"color": 0xFFFF8800, "font_size": 11})
        return str(field_default) if field_default is not None else ""

    def _build_config_field(self, field_name: str, field_info: FieldInfo, defaults: dict[str, Any]):
        """Build a single configuration field."""
        with ui.HStack(height=25, spacing=5, alignment=ui.Alignment.CENTER):
            ui.Spacer(width=20)

            # Field label
            label_text = field_name
            if field_info.is_required():
                label_text += " (required)"
            ui.Label(label_text, width=200, height=ui.Percent(1))

            # Create field
            type_display = self._get_type_display(field_info.annotation)
            default_value = self._augment_field_default_value(field_name, defaults.get(field_name))
            readonly = field_name == "name" and self._current_name and not self._register_custom_model

            # Create UI
            with ui.HStack(spacing=5):
                # Type indicator
                type_label = ui.Label(f"({type_display})", width=80, height=ui.Percent(1))
                type_label.set_style({"color": 0xFF888888})

                if readonly:
                    # Read-only label
                    ui.Label(default_value, width=310, height=ui.Percent(1))
                    string_model = ui.SimpleStringModel(default_value)
                else:
                    # Editable field
                    string_model = ui.SimpleStringModel(default_value)
                    ui.StringField(string_model, width=310, height=ui.Percent(1))

            self._config_models[field_name] = string_model

    def _on_register_clicked(self) -> None:
        """Handle register button click."""
        if not self._current_service:
            carb.log_warn("Please select a service from the dropdown")
            return

        try:
            # Collect configuration values from UI
            config_values = self._collect_config_values()

            # Determine the model name based on custom or predefined model
            if self._register_custom_model:
                # For custom models, pop name from config values to avoid duplicate kwarg
                model_name = config_values.pop("name", "").strip()
                if not model_name:
                    carb.log_warn("Please enter a model name")
                    return
            else:
                # For predefined models, use the selected name
                if self._current_name:
                    model_name = self._current_name
                    # Remove name from config_values if present to avoid duplicate kwarg
                    config_values.pop("name", None)
                else:
                    # No predefined model, try custom name from field
                    model_name = config_values.pop("name", "").strip()
                    if not model_name:
                        carb.log_warn("Please select a model from the dropdown or enter a model name")
                        return

            # Register model
            self.unified_registry.register_model(self._current_service, model_name, **config_values)

        except Exception as e:
            carb.log_error(f"Registration failed: {e}")

    def _collect_config_values(self) -> dict[str, Any]:
        """Collect all configuration values from UI widgets."""
        config_values = {}

        for field_name, model in self._config_models.items():
            # Skip "name" field when predefined model is selected
            if field_name == "name" and self._current_name and not self._register_custom_model:
                continue

            try:
                value = model.get_value_as_string().strip()

                if not value or value.lower() == "none":
                    continue  # Omit field, becomes None

                config_values[field_name] = value

            except Exception as e:
                carb.log_error(f"Error collecting value for field {field_name}: {e}")

        return config_values

    #########################################################################################
    # Config File Registration Section
    #########################################################################################
    def _inject_api_key_if_missing(self, service: str, config: dict[str, Any]) -> dict[str, Any]:
        """Inject API key from carb settings if not present in config."""
        updated_config = config.copy()

        if ModelRegistrySetting.is_service_supported(service):
            # Only inject if api_key is missing or empty
            if not updated_config.get("api_key"):
                carb_api_key = ModelRegistrySetting.get_api_key_for_service(service)
                if carb_api_key:
                    updated_config["api_key"] = carb_api_key
                    carb.log_info(f"Auto-injected API key for {service} from carb settings")
                else:
                    # Log the error but not block the registration process as some cases (e.g., local models) don't require an API key.
                    carb.log_error(f"No API key found for {service} service. Please ensure the API key is set in the carb settings if it is required. ")
            else:
                carb.log_info(f"Using provided API key for {service}")

        return updated_config


    def _on_browse_config_file(self):
        """Handle browse button click to select config file."""
        from omni.kit.window.filepicker import FilePickerDialog

        # Create file picker dialog
        FilePickerDialog(
            "Select Model Configuration File",
            allow_multi_selection=False,
            apply_button_label="Select",
            click_apply_handler=self._on_config_file_selected,
            click_cancel_handler=self._on_config_file_canceled,
            item_filter_fn=self._filter_yaml,
            file_extension_options=[("*.yaml; *.yml", "YAML Configuration Files")]
        )

    def _on_config_file_selected(self, filename, path):
        """Handle config file selected callback."""
        import os

        if filename is None or filename == "":
            return

        full_path = None
        if not path:
            full_path = filename
        else:
            full_path = os.path.join(path, filename)

        if filename.lower().endswith((".yaml", ".yml")):
            self._config_file_path_model.set_value(full_path)
            self._config_file_status_label.text = f"Selected: {filename}"
        else:
            self._config_file_status_label.text = "Please select a YAML file (.yaml or .yml)"

    def _on_config_file_canceled(self, _filename, _path):
        """Handle config file selection cancellation callback."""
        self._config_file_status_label.text = "File selection cancelled"

    def _check_is_yaml_path(self, path: str) -> bool:
        """Check if path is a YAML file."""
        return path.lower().endswith(".yaml") or path.lower().endswith(".yml")

    def _filter_yaml(self, item: Any) -> bool:
        """Filter to show only YAML files and directories."""
        if not item or item.is_folder:
            return True
        return self._check_is_yaml_path(item.path)

    def _on_register_from_config_clicked(self) -> None:
        """Handle register from config button click."""
        config_file_path = self._config_file_path_model.get_value_as_string().strip()

        if not config_file_path:
            self._config_file_status_label.text = "Error: Please select a config file first"
            carb.log_warn("No config file selected")
            return

        try:
            self._config_file_status_label.text = "Reading and processing config file..."

            # Read and parse YAML file
            import yaml
            with open(config_file_path, encoding="utf-8") as file:
                config_data = yaml.safe_load(file) or {}

            models = config_data.get("models", [])
            if not isinstance(models, list):
                raise ValueError("Config file 'models' field must be a list")

            # Inject API keys into each model configuration
            updated_models = []
            for model_config in models:
                service = model_config.get('service')
                if service:
                    updated_config = self._inject_api_key_if_missing(service, model_config)
                    updated_models.append(updated_config)
                else:
                    carb.log_warn(f"Model configuration missing 'service' field: {model_config}")
                    updated_models.append(model_config)

            self._config_file_status_label.text = "Registering models..."

            # Register models with API keys injected
            self.unified_registry.register_models(updated_models)

            self._config_file_status_label.text = "Successfully registered models from config file"
            carb.log_info(f"Successfully registered {len(updated_models)} models from config: {config_file_path}")

        except FileNotFoundError:
            self._config_file_status_label.text = "Error: Config file not found"
            carb.log_error(f"Config file not found: {config_file_path}")
        except Exception as e:
            error_msg = str(e)
            self._config_file_status_label.text = f"Error: {error_msg[:50]}{'...' if len(error_msg) > 50 else ''}"
            carb.log_error(f"Failed to register models from config: {error_msg}")