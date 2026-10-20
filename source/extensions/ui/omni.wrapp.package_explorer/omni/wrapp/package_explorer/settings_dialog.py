# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
from typing import Callable, Dict

import carb.settings
import omni.client
import omni.ui as ui

from .style import ICON_PATH, UI_STYLES
from .utils import (
    AssetRepo,
    call_async,
    get_s3_region_and_bucket,
    get_stage_dir_and_name,
    is_s3_http_uri,
    is_s3_uri,
    s3_to_http_uri,
    set_omni_client_s3_configuration,
)


class SettingsData:
    def __init__(self, asset_repos: Dict[str, AssetRepo] | None = None):
        """
        Initialize settings data with asset repos.

        Args:
            asset_repos: Dictionary mapping repo_key -> AssetRepo
        """
        self.asset_repos = asset_repos if asset_repos is not None else {}
        # Only sort existing repos, not newly added ones
        if asset_repos is not None:
            self.asset_repos = dict(sorted(self.asset_repos.items(), key=lambda item: item[0].lower()))

    def set_asset_repo_name(self, key: str, name: str):
        self.set_asset_repo_display_name(key, name)

    def set_asset_repo_display_name(self, key: str, display_name: str):
        if key in self.asset_repos:
            self.asset_repos[key].display_name = display_name

    def set_asset_repo_install_path(self, key: str, install_path: str):
        if key in self.asset_repos:
            self.asset_repos[key].install_path = install_path

    def set_asset_repo_url(self, key: str, url: str):
        if key in self.asset_repos:
            self.asset_repos[key].publish_uri = url

    def add_asset_repo(self, repo_key: str, display_name: str, url: str, install_path: str):
        self.asset_repos[repo_key] = AssetRepo(display_name=display_name, publish_uri=url, install_path=install_path)

    def remove_asset_repo(self, key: str):
        if key in self.asset_repos:
            del self.asset_repos[key]


class SettingsDialog:

    _STYLE_LABEL_WIDTH = 120

    def __init__(
        self,
        click_okay_handler: None | Callable[["SettingsDialog"], None],
        click_cancel_handler: None | Callable[["SettingsDialog"], None],
        asset_repos: Dict[str, AssetRepo] | None = None,
    ):
        self._stage_dir = get_stage_dir_and_name()[0]

        # UI
        self._window: ui.Window | None = None
        self._asset_repo_stack: ui.VStack | None = None
        self._scrolling_frame: ui.ScrollingFrame | None = None
        self._asset_repos: dict[
            str, tuple[ui.StringField, ui.Button, ui.StringField, ui.StringField, ui.StringField]
        ] = {}  # key -> (key_field, remove_button, display_name_field, url_field, install_path_field)
        self._width = 1200
        self._min_height = 480  # Minimum height to ensure buttons are visible

        self._add_asset_repo_button: ui.Button | None = None
        self._add_asset_repo_msg: ui.Label | None = None
        self._ok_button: ui.Button | None = None
        self._cancel_button: ui.Button | None = None

        settings = carb.settings.get_settings()
        self._theme = settings.get_as_string("/persistent/app/window/uiStyle") or "NvidiaDark"
        self._style = UI_STYLES[self._theme]

        self._click_okay_handler = click_okay_handler
        self._click_cancel_handler = click_cancel_handler

        self._data = SettingsData(asset_repos)

    async def _asset_url_changed_async(
        self,
        input_url: str,
        repo_key: str,
        key_field: ui.StringField,
        name_field: ui.StringField,
        install_path_field: ui.StringField,
    ):
        if not input_url:
            self._add_asset_repo_msg.text = "Please specify a URL to search for repos."
            return

        name = name_field.model.get_value_as_string()
        repo_key_from_field = key_field.model.get_value_as_string() if isinstance(key_field, ui.StringField) else name
        install_path = install_path_field.model.get_value_as_string()

        # Determine if we should auto-generate name and install path
        should_auto_generate_name = not name
        should_auto_generate_install_path = not install_path
        should_auto_generate_key = not repo_key or str(repo_key).startswith(
            "__new_repo_"
        )  # If repo_key is not provided, or starts with "__new_repo_", we auto-generate the key.

        # Take the first name which does not start with a '.' (and is not empty, the string ends with a slash)
        if should_auto_generate_name:
            repo_name_candidates = input_url.split("/")

            for rn in reversed(repo_name_candidates):
                if rn and not rn.startswith("."):
                    repo_name = rn
                    break
        else:
            repo_name = name.strip()

        if should_auto_generate_install_path:
            repo_install_path = f"./{repo_name}/"
        else:
            repo_install_path = install_path.strip()
            if not repo_install_path.endswith("/"):
                repo_install_path = repo_install_path + "/"

        key_field, _, name_field, _, install_path_field = self._asset_repos[repo_key]

        # Update the fields that should change
        if should_auto_generate_name:
            name_field.model.set_value(repo_name)
        if should_auto_generate_install_path:
            install_path_field.model.set_value(repo_install_path)
        if should_auto_generate_key:
            repo_key = (repo_key_from_field or repo_name) if should_auto_generate_key else repo_key
            key_field.model.set_value(repo_key)

        # Clear any error message
        self._add_asset_repo_msg.text = ""

    def _asset_url_changed(
        self,
        repo_url: str,
        repo_key: str,
        key_field: ui.StringField,
        name_field: ui.StringField,
        install_path_field: ui.StringField,
    ):
        asyncio.ensure_future(
            self._asset_url_changed_async(repo_url, repo_key, key_field, name_field, install_path_field)
        )

    def _asset_key_changed(self, repo_key: str):
        asyncio.ensure_future(self._asset_key_changed_async(repo_key))

    async def _asset_key_changed_async(self, repo_key: str):
        if repo_key in self._asset_repos:
            self._add_asset_repo_msg.text = f"Repo key '{repo_key}' already exists."
        else:
            self._add_asset_repo_msg.text = ""

    def _build_asset_repo_row(self, repo_key: str, new_repo: bool = False):
        # If this is a new repo, we allow user to edit the repo key.
        if new_repo:
            asset_repo_key = ui.StringField(
                identifier="txt_asset_repo_key",
                width=self._STYLE_LABEL_WIDTH,
                height=20,
                tooltip=f"Name of repo: '{repo_key}'",
                style=self._style,
            )
        else:
            asset_repo_key = ui.StringField(
                identifier="lbl_asset_repo_name",
                width=self._STYLE_LABEL_WIDTH,
                height=20,
                tooltip=f"Name of repo: '{repo_key}'",
                read_only=True,
                style={"Field": {"background_color": 0x00000000, "color": 0xFFD6D6D6}},
            )
            asset_repo_key.model.set_value(repo_key)
        asset_remove_button = ui.Button(
            identifier="btn_asset_remove",
            image_width=16,
            image_height=18,
            width=22,
            height=20,
            visible=True,
            tooltip=f"Remove asset repo '{repo_key}'",
            image_url=f"{ICON_PATH}/trash_can.svg",
            style={"margin": 1, "padding": 2},
            clicked_fn=lambda repo_key=repo_key: self._remove_asset_repo(repo_key),
        )
        asset_repo_display_name = ui.StringField(
            identifier="txt_asset_repo_display_name",
            width=self._STYLE_LABEL_WIDTH,
            height=20,
            tooltip=f"Display name of repo: '{repo_key}'",
            style=self._style,
        )

        asset_repo_url = ui.StringField(
            identifier="txt_asset_repo_url",
            height=20,
            tooltip=f"URL of repo '{repo_key}'",
            style=self._style,
        )

        asset_repo_install_path = ui.StringField(
            identifier="txt_asset_repo_install_path",
            width=ui.Percent(20),
            height=20,
            tooltip=f"Install path used for packages from repo '{repo_key}'",
            style=self._style,
        )

        # Add value change handlers to update the data model
        asset_repo_url.model.add_end_edit_fn(
            lambda model: self._asset_url_changed(
                model.get_value_as_string(),
                repo_key=repo_key,
                key_field=asset_repo_key,
                name_field=asset_repo_display_name,
                install_path_field=asset_repo_install_path,
            )
        )
        asset_repo_key.model.add_end_edit_fn(lambda model: self._asset_key_changed(model.get_value_as_string()))

        # Add the UI elements to the dict
        self._asset_repos[repo_key] = (
            asset_repo_key,
            asset_remove_button,
            asset_repo_display_name,
            asset_repo_url,
            asset_repo_install_path,
        )
        return asset_repo_key, asset_repo_display_name, asset_repo_url, asset_repo_install_path

    def _on_add_repo_clicked(self):
        with self._asset_repo_stack:
            with ui.HStack(height=0, spacing=4):
                # Generate a temporary unique key for the new repo
                repo_key = f"__new_repo_{len(self._asset_repos)}__"
                self._build_asset_repo_row(repo_key, new_repo=True)

        # Scroll to the bottom of the scrolling frame so the new empty repo entry is visible
        if self._scrolling_frame:
            self._scrolling_frame.scroll_y = self._scrolling_frame.scroll_y_max + 100

    def _remove_asset_repo(self, repo_key: str):
        # Find the repo in the UI dict
        if repo_key in self._asset_repos:
            # Remove the UI elements
            key_field, remove_button, name_field, url_field, install_path_field = self._asset_repos.pop(repo_key)
            key_field.visible = False
            key_field.destroy()
            remove_button.visible = False
            remove_button.destroy()
            name_field.visible = False
            name_field.destroy()
            url_field.visible = False
            url_field.destroy()
            install_path_field.visible = False
            install_path_field.destroy()

            # Clear any error message
            self._add_asset_repo_msg.text = ""

    async def _update_asset_repo_list(self):
        # Clear existing UI elements
        for key_field, remove_button, name_field, url_field, install_path_field in self._asset_repos.values():
            key_field.destroy()
            remove_button.destroy()
            name_field.destroy()
            url_field.destroy()
            install_path_field.destroy()
        self._asset_repos = {}
        self._asset_repo_stack.clear()

        # Rebuild the UI
        with self._asset_repo_stack:
            with ui.HStack(height=0, spacing=4):
                ui.Label(
                    "\tRepository",
                    width=self._STYLE_LABEL_WIDTH,
                    style=self._style,
                    alignment=ui.Alignment.RIGHT_CENTER,
                )
                ui.Label("", style=self._style, width=22)
                ui.Label("Display Name", style=self._style, width=self._STYLE_LABEL_WIDTH)
                ui.Label("Publish URL", style=self._style, tooltip="Uri where CIP processed assets are published")
                ui.Label(
                    "Install Path",
                    style=self._style,
                    width=ui.Percent(20),
                    tooltip="Uri where assets are installed, ie: S3",
                )

            ui.Line(height=9)

            for repo_key, repo in self._data.asset_repos.items():
                with ui.HStack(height=0, spacing=4):
                    key_field, asset_repo_display_name, asset_repo_url, asset_repo_install_path = (
                        self._build_asset_repo_row(repo_key)
                    )
                    # Set values from data model
                    asset_repo_display_name.model.set_value(repo.display_name)
                    asset_repo_url.model.set_value(repo.publish_uri)
                    asset_repo_install_path.model.set_value(repo.install_path)

    def _build_ui(self):
        self._window = ui.Window(
            "Package Explorer Settings",
            width=self._width,
            height=self._min_height,
            flags=ui.WINDOW_FLAGS_POPUP | ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_MODAL,
        )

        with self._window.frame:
            with ui.VStack(spacing=6):
                # Make the repo stack section scrollable
                with ui.ScrollingFrame(
                    height=ui.Fraction(0.9),  # The scrollable area will take 90% the height of the main VStack.
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                ) as self._scrolling_frame:
                    self._asset_repo_stack = ui.VStack(spacing=3)
                    asyncio.ensure_future(self._update_asset_repo_list())

                # Message area outside the scrollable frame
                with ui.HStack(height=30, spacing=4):  # Increased height to accommodate multiple lines
                    self._add_asset_repo_msg = ui.Label(
                        "", width=800, word_wrap=True, height=40, style={"color": ui.color.red}
                    )  # Fixed height for the label

                ui.Spacer(height=10)  # Add spacing between message and buttons

                with ui.HStack(
                    height=ui.Fraction(0.1), spacing=4
                ):  # The button area will take 10% the height of the main VStack.
                    self._add_asset_repo_button = ui.Button(
                        "+ Add Repo",
                        width=100,
                        height=20,
                        style=self._style,
                        tooltip="Add a new repo",
                        clicked_fn=self._on_add_repo_clicked,
                    )
                    ui.Spacer()
                    self._ok_button = ui.Button("Save", width=100, height=20, style=self._style)
                    self._ok_button.set_clicked_fn(lambda: self._on_okay(self._click_okay_handler))
                    self._cancel_button = ui.Button("Cancel", width=100, height=20, style=self._style)
                    self._cancel_button.set_clicked_fn(lambda: self._on_cancel(self._click_cancel_handler))

                ui.Spacer(height=2)

    @property
    def asset_repos(self) -> list[tuple[str, str, str]]:
        return self._data.asset_repos

    def _validate_asset_repo_fields(self) -> str | None:
        """Validate asset repo fields are not empty."""
        existing_keys = []
        for key_field, _, name_field, url_field, install_path_field in self._asset_repos.values():
            key = key_field.model.get_value_as_string()
            if key in existing_keys:
                return f"Repo '{key}' Key already exists."
            existing_keys.append(key)

            name = name_field.model.get_value_as_string()
            if not key or not key.strip():
                return f"Repo '{key}' Key cannot be empty."
            if not name or not name.strip():
                return f"Repo '{key}' Name cannot be empty."
            url = url_field.model.get_value_as_string()
            if not url or not url.strip():
                return f"Repo '{key}' URL cannot be empty."
            install_path = install_path_field.model.get_value_as_string()
            if not install_path or not install_path.strip():
                return f"Repo '{key}' Install path cannot be empty."

    async def _validate_asset_repo_urls(self) -> str | None:
        """Validate asset repo URLs."""
        for key_field, _, name_field, url_field, _ in self._asset_repos.values():
            key = key_field.model.get_value_as_string()
            check_url = url_field.model.get_value_as_string()
            display_name = name_field.model.get_value_as_string()
            # Strip /.packages/ from the URL if present
            if check_url.endswith("/.packages/"):
                check_url = check_url[: -len("/.packages/")]

            if check_url.startswith("./") or check_url.startswith("../"):
                check_url = omni.client.combine_urls(self._stage_dir, check_url)

            # Convert s3:// to https:// - omni.client.stat only supports https://
            if is_s3_uri(check_url):
                check_url = s3_to_http_uri(check_url)

            if is_s3_http_uri(check_url):
                region, bucket, bucket_uri = get_s3_region_and_bucket(check_url)
                set_omni_client_s3_configuration(bucket_uri, bucket, region)

            r, _ = await omni.client.stat_async(check_url)
            if r != omni.client.Result.OK:
                return f"{r}: Asset repo '{display_name} ({key})': '{url_field.model.get_value_as_string()}' is not a valid WRAPP repo URL."

    async def _validate_settings_async(self) -> str | None:
        """Validate all settings and return error message if any, None if all valid."""
        # Validate asset repo fields
        error = self._validate_asset_repo_fields()
        if error:
            return error

        # Validate asset repo URLs
        error = await self._validate_asset_repo_urls()
        if error:
            return error

    def _on_okay(self, callback: None | Callable[["SettingsDialog"], None]) -> None:
        # Start async validation
        call_async(self._validate_and_save_async(callback))

    def _build_asset_repo_dict(self) -> dict[str, AssetRepo]:
        """Build a dictionary of asset repos from the UI."""
        asset_repos = {}
        for key_field, _, name_field, url_field, install_path_field in self._asset_repos.values():
            key = key_field.model.get_value_as_string()
            name = name_field.model.get_value_as_string()
            url = url_field.model.get_value_as_string()
            install_path = install_path_field.model.get_value_as_string()
            asset_repos[key] = AssetRepo(display_name=name, publish_uri=url, install_path=install_path)
        return asset_repos

    async def _validate_and_save_async(self, callback: None | Callable[["SettingsDialog"], None]) -> None:
        # Collect all asset repos from the UI. No empty entries also update __new_repo_<index>__ keys to the actual repo name.
        asset_repos = self._build_asset_repo_dict()
        self._data.asset_repos = asset_repos

        # Validate all settings
        error_message = await self._validate_settings_async()
        if error_message:
            # Display error and don't close dialog
            self._add_asset_repo_msg.text = error_message
            return

        # Clear any previous error messages
        self._add_asset_repo_msg.text = ""

        # All validation passed, proceed with save
        if callback:
            callback(self)
        else:
            self.hide()

    def _on_cancel(self, callback: None | Callable[["SettingsDialog"], None]):
        if callback:
            callback(self)
        else:
            self.hide()

    def show(self):
        self._build_ui()
        self._window.visible = True

    def hide(self):
        self._window.visible = False

    def destroy(self):
        self._asset_repos = None
        self._asset_repo_stack = None
        self._ok_button = None
        self._cancel_button = None
        self._window = None
