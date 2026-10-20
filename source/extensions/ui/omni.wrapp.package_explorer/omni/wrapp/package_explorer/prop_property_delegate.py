# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import functools
from typing import List, Optional, Union

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit.async_engine import run_coroutine

from .asset import AssetType
from .browser_model import WrappAssetDetailItem
from .browser_property_delegate import BrowserPropertyDelegate
from .property_widgets import PropAssetTagsWidget
from .utils import call_async


class ProgressValueModel(ui.AbstractValueModel):
    """A custom model that can be used for progress bar, it can be a float or a string"""

    def __init__(self, value: Union[float, str] = 0.0):
        """Initialize the ProgressValueModel"""
        super().__init__()
        self._progress_str: str = str(value)
        self._progress: float = 0.0
        self.set_value(value)

    def set_value(self, value: float, text: Union[float, str] = None):
        """Reimplemented set"""
        try:
            progress = float(value)
            progress_str = text or f"{progress * 100:.2f}%"
        except ValueError:
            # If the value is not a float, use the previous progress and only update the progress string
            progress = self._progress
            progress_str = str(value)

        # Update the progress and the progress string if they are different
        if progress_str != self._progress_str or progress != self._progress:
            # Tell the widget that the model is changed
            self._progress_str = progress_str
            self._progress = progress
            self._value_changed()

    def get_value_as_float(self):
        """Get the progress as a float"""
        return self._progress

    def get_value_as_string(self):
        """Get the progress as a string"""
        return str(self._progress_str)


class PropWrappAssetPropertyDelegate(BrowserPropertyDelegate):
    """Delegate for displaying and managing WRAPP asset properties.

    Handles:
    - Asset property display
    - Version management
    - Installation controls
    - Hierarchy navigation
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uninstall_button = None
        self._progress_bar = None
        self._progress_bar_model = ProgressValueModel()

    def accepted(self, item: Optional[WrappAssetDetailItem]) -> bool:
        """Check if this delegate can handle the given asset item.

        Args:
            item (Optional[WrappAssetDetailItem]): The asset item to check

        Returns:
            bool: True if this delegate can handle the item, False otherwise
        """
        return item and item.asset.asset_type == AssetType.GENERIC

    def show(self, item: Optional[WrappAssetDetailItem], frame: ui.Frame) -> None:
        """Display the asset properties in the given frame.

        Args:
            item (Optional[WrappAssetDetailItem]): The asset item to display
            frame (ui.Frame): The frame to display the properties in
        """
        if item is None:
            return
        asset = item.asset
        self._item = item
        # Show existing container
        if hasattr(self, "_container"):
            self._container.visible = True
            self._name_label.text = asset.name
            self._source_url_value.model.set_value(self._item.url_to_update)
            if hasattr(self, "h_buttons"):
                self._h_hstack.clear()

            with self._h_hstack:
                self._build_hierarchy_links()

            # Reset the version and the thumbnail to the current version
            self._item.version_to_update = asset.version
            self._thumbnail_img.source_url = asset.thumbnail
            self._tags_field.tags = asset.tags

            # Update the version combobox model if it is not the same as the item's versions model
            if self._version_combobox.model != item.versions_model:
                self._version_combobox.model = item.versions_model
                self._version_combobox.model.add_item_changed_fn(self._update_thumbnail)
                self._version_combobox.model.add_item_changed_fn(self._update_source_url)

            # Update the uninstall button visibility
            self._uninstall_button.visible = item.installed

            # Set the current progress of the progress bar
            item.set_on_wrapp_progress_updated_fn(functools.partial(self._update_progress_bar_fn, self._item))
            if item.progress_type:
                self._progress_bar.model.set_value(0, f"{item.progress_type} in queue")
            else:
                self._progress_bar.model.set_value(0, "No process running")

        else:
            # Create new container - first time setup
            with frame:
                self._container = ui.VStack(height=0, spacing=5)
                with self._container:
                    self._build_thumbnail(item)
                    with ui.HStack():
                        ui.Spacer()
                        self._name_label = ui.Label(asset.name, height=0, style_type_name_override="Asset.Title")
                        ui.Spacer()

                    with ui.CollapsableFrame("Asset info"):
                        self.collapse_info = self._build_info_widget()

                    with ui.CollapsableFrame("Tags", height=ui.Percent(100)):
                        self._tags_field = self._build_tags()

                    with ui.CollapsableFrame("Progress", height=ui.Percent(100)):
                        self._progress_bar = self._build_progress_bar()

                    ui.Spacer()

    def accepted_multiple(self, detail_items: List[WrappAssetDetailItem]) -> bool:
        """BrowserPropertyDelegate method override"""
        return False

    def show_multiple(self, detail_items: List[WrappAssetDetailItem], frame: ui.Frame) -> None:
        """BrowserPropertyDelegate method override"""
        pass

    def _build_thumbnail(self, item: WrappAssetDetailItem):
        """Builds thumbnail frame and resizes"""
        self._thumbnail_frame = ui.Frame(height=0)
        self._thumbnail_frame.set_computed_content_size_changed_fn(self._on_thumbnail_frame_size_changed)

        with self._thumbnail_frame:
            with ui.HStack():
                ui.Spacer(width=ui.Percent(25))

                self._thumbnail_container = ui.ZStack(height=ui.Fraction(1))
                with self._thumbnail_container:
                    self._thumbnail_img = ui.Image(
                        item.asset.thumbnail,
                        fill_policy=ui.FillPolicy.PRESERVE_ASPECT_FIT,
                        alignment=ui.Alignment.CENTER_TOP,
                    )
                    # Badge to indicate item. Not used for WRAPP assets currently.
                    self._badge_container = ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM, visible=False)
                    with self._badge_container:
                        ui.Spacer(width=ui.Percent(80))
                        with ui.VStack():
                            ui.Spacer(height=2)
                            ui.ImageWithProvider(
                                fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT,
                                alignment=ui.Alignment.LEFT,
                                style_type_name_override="GridView.Item.Badge.Image",
                            )
                ui.Spacer(width=ui.Percent(25))

    def _build_tags(self):
        """Add the tag link section. must pass explorer instance"""
        from .extension import get_instance

        browser_widget = get_instance().browser_widget
        tag_widget = PropAssetTagsWidget(self._item.asset.tags, browser_widget)
        return tag_widget

    def _build_info_widget(self):
        """Build the Asset information section"""
        with ui.VStack(spacing=10):
            with ui.HStack(spacing=3):
                self._version_combobox = self._build_combobox("Version:", self._item.versions_model)
                self._version_combobox.model.add_item_changed_fn(self._update_thumbnail)
                self._version_combobox.model.add_item_changed_fn(self._update_source_url)
                self._install_button = ui.Button(
                    "Install",
                    alignment=ui.Alignment.RIGHT_BOTTOM,
                    clicked_fn=self._on_install_button_clicked,
                    spacing=0,
                    width=ui.Percent(24),
                )
                self._uninstall_button = ui.Button(
                    "Uninstall",
                    alignment=ui.Alignment.RIGHT_BOTTOM,
                    clicked_fn=self._on_uninstall_button_clicked,
                    spacing=0,
                    width=ui.Percent(24),
                )
                self._uninstall_button.visible = self._item.installed

            with ui.HStack():
                self._source_url_label = ui.Label("Source URL:", style_type_name_override="Asset.Label", width=100)
                self._source_url_value = ui.StringField(
                    alignment=ui.Alignment.LEFT_BOTTOM,
                    style_type_name_override="Asset.Value",
                    width=ui.Percent(75),
                    read_only=True,
                )
                self._source_url_value.model.set_value(self._item.url_to_update)
            self._h_hstack = ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM)
            with self._h_hstack:
                self._hierachy_label = ui.Label("Hierarchy:", style_type_name_override="Asset.Label", width=100)
                self._build_hierarchy_links()
            ui.Spacer()

    def _build_progress_bar(self):
        """Build the Progress section"""
        with ui.VStack(spacing=10):
            with ui.HStack():
                self._progress_bar_model.set_value(0, "No process running")
                progress_bar = ui.ProgressBar(self._progress_bar_model)
            ui.Spacer()
        return progress_bar

    def _get_gradient_color(self, progress: float) -> int:
        """Calculate gradient color from mid-blue to dark blue based on progress (0.0 to 1.0)."""
        # Remap progress from [0, 1] to [0.5, 1] for color interpolation
        # Mid-blue (progress=0): RGB(142, 159, 215)
        # Dark blue (progress=1): RGB(30, 64, 175)
        progress = max(0.0, min(1.0, progress))  # Clamp to [0, 1]
        t = 0.5 + (progress * 0.5)  # Remap to [0.5, 1.0]
        r = int(255 - (255 - 30) * t)
        g = int(255 - (255 - 64) * t)
        b = int(255 - (255 - 175) * t)
        return 0xFF000000 | (b << 16) | (g << 8) | r

    def _update_progress_bar_fn(self, item, progress: float):
        """Update the progress bar.

        Args:
            item: The item whose progress_type will be read dynamically
            progress: Progress value from 0.0 to 1.0
        """
        if not self._progress_bar or not self._progress_bar_model:
            return

        # We only update the progress bar if the item is the same as the item in the delegate
        if item != self._item:
            return

        # Read progress_type dynamically from the item
        progress_type = item.progress_type if item.progress_type else "Process"

        if progress >= 1.0:
            message = f"{progress_type} completed"
        else:
            message = f"{progress_type}ing... {progress * 100:.2f}%"

        self._progress_bar_model.set_value(progress, message)
        self._progress_bar.set_style({"color": self._get_gradient_color(progress)})

    def _on_install_button_clicked(self):
        """Handle installation of WRAPP package when install button is clicked."""

        def update_future_done_callback(future=None):
            self._install_button.enabled = True
            self._install_button.text = "Install"
            if future and future.exception():
                carb.log_error(
                    f"Failed to install asset {self._item.asset.name} version {self._item.asset.version} ({self._item.asset.url}) "
                    f"error: {str(future.exception())}"
                )
                raise future.exception()

        self._install_button.enabled = False
        self._install_button.text = "Installing..."
        # Set progress type so it's read dynamically by the callback
        self._item.progress_type = "Install"
        self._item.set_on_wrapp_progress_updated_fn(functools.partial(self._update_progress_bar_fn, self._item))
        future = run_coroutine(self._item.update())
        future.add_done_callback(update_future_done_callback)

    def _on_uninstall_button_clicked(self):
        """Handle uninstallation of WRAPP package when uninstall button is clicked."""
        if not self._uninstall_button:
            return

        def uninstall_future_done_callback(future=None):
            self._uninstall_button.enabled = True
            self._uninstall_button.text = "Uninstall"
            if future and future.exception():
                carb.log_error(
                    f"Failed to uninstall asset {self._item.asset.name} version {self._item.asset.version} ({self._item.asset.url}) "
                    f"error: {str(future.exception())}"
                )
                raise future.exception()
            # Hide the uninstall button after uninstallation is successfully done
            self._uninstall_button.visible = False

        self._uninstall_button.enabled = False
        self._uninstall_button.text = "Uninstalling..."
        # Set progress type so it's read dynamically by the callback
        self._item.progress_type = "Uninstall"
        self._item.set_on_wrapp_progress_updated_fn(functools.partial(self._update_progress_bar_fn, self._item))
        future = run_coroutine(self._item.uninstall())
        future.add_done_callback(uninstall_future_done_callback)

    def _update_thumbnail(self, *args, **kwargs):
        """Update thumbnail"""
        self._thumbnail_img.source_url = self._item.thumbnail_to_update

    def _update_source_url(self, *args, **kwargs):
        """Update source url"""
        self._source_url_value.model.set_value(self._item.url_to_update)

    def _build_hierarchy_links(self):
        """Build clickable hierarchy links for asset navigation."""
        from .extension import get_instance

        browser_widget = get_instance().browser_widget

        def on_click(value: List[str]):
            """set the browse search field with this tag

            Args:
                value (List): tag search value
            """
            search_field = browser_widget.search_field
            search_field.search_words = value

        self.h_buttons = []
        hierarchy = self._item.asset.hierarchy.strip("/").split("/")
        for i, h in enumerate(hierarchy):
            text_v = "{}".format(h)

            new_button = ui.Button(
                text_v,
                alignment=ui.Alignment.LEFT_BOTTOM,
                spacing=0,
                width=0,
                style_type_name_override="Asset.ButtonLinks",
            )
            h_list = hierarchy[0 : (i + 1)]
            new_button.set_clicked_fn(lambda value=h_list: on_click(value))

            if i < (len(hierarchy) - 1):
                ui.Label(" > ", width=0)
            self.h_buttons.append(new_button)

    def clear_buttons(self, buttons):
        for b in buttons:
            b.visible = False

    def _on_thumbnail_frame_size_changed(self):
        # Dynamic change thumbnail size to be half of frame width
        async def __change_thumbnail_size_async():
            await omni.kit.app.get_app().next_update_async()
            image_size = self._thumbnail_frame.computed_width / 2
            self._thumbnail_img.height = ui.Pixel(image_size)

        call_async(__change_thumbnail_size_async())
