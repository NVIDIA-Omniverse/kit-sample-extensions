import asyncio
import os
import re
import traceback
import urllib
from typing import Callable, List, Tuple

import carb
import omni.client
import omni.client.utils as clientutils
import omni.ui
import psutil
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.window.filepicker import FilePickerDialog

try:
    from omni.kit.window.filepicker import DetailFrameController
except ImportError:
    DetailFrameController = None

from . import FileBrowserMode, FileBrowserSelectionType

__all__ = ["FileBrowserUI", "FilePickerApp"]


class FileBrowserUI:
    def __init__(
        self,
        title: str,
        mode: FileBrowserMode,
        selection_type: FileBrowserSelectionType,
        filter_options: List[Tuple[str, str]],
        save_extensions: List[str] = [],
        apply_button_name: str = "",
        allow_multi_selection=False,
        build_options_pane_fn: Callable[[List[FileBrowserItem]], bool] = None,
        on_selection_changed: Callable[[List[FileBrowserItem]], bool] = None,
    ):
        confirm_text = "Import"
        if apply_button_name != "":
            confirm_text = apply_button_name
        self._file_picker = FilePickerApp(
            title,
            confirm_text,
            mode,
            selection_type,
            filter_options,
            save_extensions,
            allow_multi_selection,
            build_options_pane_fn,
            on_selection_changed,
        )

    def destroy(self):
        self._file_picker.destroy()
        self._file_picker = None

    def set_current_directory(self, dir: str):
        self._file_picker.set_current_directory(dir)

    def set_current_filename(self, filename: str):
        self._file_picker.set_current_filename(filename)

    def open(self, select_fn: Callable[[List[str]], None], cancel_fn: Callable[[], None]):
        self._file_picker.set_custom_fn(select_fn, cancel_fn)
        self._file_picker.show_dialog()

    def destroy(self):
        self._file_picker.destroy()
        self._file_picker = None


class FilePickerApp:
    """
    Standalone app to demonstrate the use of the FilePicker dialog.

    Args:
        title (str): Title of the window.
        apply_button_name (str): Name of the confirm button.
        mode (FileBrowserMode): The file picker mode that whether it's to open or save.
        selection_type (FileBrowserSelectionType): The file type that confirm event will respond to.
        item_filter_options (list): Array of filter options. Element of array is a tuple that first element of this tuple is the regex string for filtering, and second element of this tuple is the descriptions, like ("*.*", "All Files"). By default, it will list all files.
        save_extensions: The real extension name that will be saved.
        allow_multi_selections: Allow to select multiple files.
        build_options_pane_fn (Callable[[List[FileBrowserItem]], bool]): Function to build options panel.
        on_selection_changed (Callable[[List[FileBrowserItem]], bool]): Function to monitor selection changed.
    """

    def __init__(
        self,
        title: str,
        apply_button_name: str,
        mode: FileBrowserMode,
        selection_type: FileBrowserSelectionType = FileBrowserSelectionType.ALL,
        item_filter_options: list = [("*.*", "All Files (*.*)")],
        save_extensions: list = [".usd"],
        allow_multi_selections: bool = False,
        build_options_pane_fn: Callable[[List[FileBrowserItem]], bool] = None,
        on_selection_changed: Callable[[List[FileBrowserItem]], bool] = None,
    ):
        self._title = title
        self._filepicker = None
        self._mode = mode
        self._selection_type = selection_type
        self._custom_select_fn = None
        self._custom_cancel_fn = None
        self._apply_button_name = apply_button_name
        self._filter_regexes = []
        self._filter_descriptions = []
        self._current_directory = None
        self._allow_multi_selections = allow_multi_selections
        self._build_options_pane_fn = build_options_pane_fn
        self._selection_changed_fn = on_selection_changed
        self._selected_items = []
        self._options_detail_controller = None
        self._options_detail_frame_name = "Import Options"
        for item in item_filter_options:
            self._filter_regexes.append(re.compile(item[0], re.IGNORECASE))
            self._filter_descriptions.append(item[1])
        self._save_extensions = save_extensions
        self._build_ui()

    def destroy(self):
        self._custom_select_fn = None
        self._custom_cancel_fn = None
        self._build_options_pane_fn = None
        self._on_selection_changed = None
        self._options_detail_controller = None
        self._filepicker.destroy()
        self._filepicker = None

    def set_custom_fn(self, select_fn: Callable[[List[str]], None], cancel_fn: Callable[[], None]):
        self._custom_select_fn = select_fn
        self._custom_cancel_fn = cancel_fn

    def show_dialog(self):
        self._filepicker.show(self._current_directory)
        self._current_directory = None

    def hide_dialog(self):
        self._filepicker.hide()

    def set_current_directory(self, dir: str):
        self._current_directory = dir
        if not self._current_directory.endswith("/"):
            self._current_directory += "/"

    def set_current_filename(self, filename: str):
        self._filepicker.set_filename(filename)

    def _build_ui(self):
        # Create the dialog
        kwargs = {
            "allow_multi_selection": self._allow_multi_selections,
            "apply_button_label": self._apply_button_name,
            "click_apply_handler": self._on_click_open,
            "click_cancel_handler": self._on_click_cancel,
            "item_filter_options": self._filter_descriptions,
            "item_filter_fn": lambda item: self._on_filter_item(item),
            "error_handler": lambda m: self._on_error(m),
            "selection_changed_fn": self._on_selection_changed,
            "filename_changed_handler": self._on_filename_changed,
        }

        if self._build_options_pane_fn:
            if DetailFrameController:
                kwargs["show_detail_view"] = True
            else:
                kwargs["options_pane_build_fn"] = self._build_options_pane

        self._filepicker = FilePickerDialog(self._title, **kwargs)

        if (
            self._build_options_pane_fn
            and DetailFrameController
            and hasattr(self._filepicker, "add_detail_frame_from_controller")
        ):
            self._refresh_options_detail_frame()

        if self._selection_type == FileBrowserSelectionType.DIRECTORY_ONLY:
            self._filepicker.set_filebar_label_name("Folder name")
        elif self._selection_type == FileBrowserSelectionType.FILE_ONLY:
            self._filepicker.set_filebar_label_name("File name")
        else:
            self._filepicker.set_filebar_label_name("File or Folder name")

        # OM-78341: apply button should start off disabled
        # -- TRANSITION START
        # this method is only available in more recent Kit 105
        if hasattr(self._filepicker._widget.file_bar, "enable_apply_button"):
            self._filepicker._widget.file_bar.enable_apply_button(enable=False)
        # -- TRANSITION END

        # Start off hidden
        self.hide_dialog()

    def _on_selection_changed(self, items: List[FileBrowserItem]):
        if self._selection_changed_fn:
            self._selection_changed_fn(items)

        self._selected_items = items or []
        self._refresh_options_detail_frame()

        if len(items) != 1:
            return False

        item = items[0]
        if item.is_folder and self._selection_type == FileBrowserSelectionType.FILE_ONLY:
            self._filepicker._widget.file_bar.enable_apply_button(enable=False)
            return False

        if not item.is_folder and self._selection_type == FileBrowserSelectionType.DIRECTORY_ONLY:
            self._filepicker._widget.file_bar.enable_apply_button(enable=False)
            return False

        self._update_import_btn_state(item.path)

        # OM-85377: Pass in the full item path for setting current filename, so when the
        # selected item is not directly under the current directory, the filename includes
        # all the folder structure in between
        self.set_current_filename(item.path)

    def _on_filename_changed(self, filename):
        # OM-78341: Disable apply button if no file is selected
        # -- TRANSITION START
        # this method is only available in more recent Kit 105
        if self._filepicker and hasattr(self._filepicker._widget.file_bar, "enable_apply_button"):
            self._filepicker._widget.file_bar.enable_apply_button(enable=bool(filename))
        # -- TRANSITION END

        current_directory = self._filepicker.get_current_directory()
        if current_directory and current_directory.endswith("/"):
            current_directory += "/"
            filepath = omni.client.combine_urls(current_directory, filename)
        else:
            filepath = filename
        if self._update_import_btn_state(filepath):
            self._selected_items = [filepath]
        else:
            self._selected_items = []
        self._refresh_options_detail_frame()

    def _update_import_btn_state(self, filepath):
        """
        Enable or disable the import button state based on whether the file path is valid
        """
        result, _ = omni.client.stat(filepath)
        valid = result == omni.client.Result.OK
        self._filepicker._widget.file_bar.enable_apply_button(enable=valid)
        return valid

    def _build_options_pane(self, items=None):
        if not self._build_options_pane_fn:
            return False

        try:
            return self._build_options_pane_fn(items or self._selected_items)
        except Exception:
            carb.log_error(f"Failed to build Asset Importer options pane:\n{traceback.format_exc()}")
            return False

    def _refresh_options_detail_frame(self):
        if not self._build_options_pane_fn or not self._filepicker or not DetailFrameController:
            return

        if not hasattr(self._filepicker, "add_detail_frame_from_controller"):
            return

        if hasattr(self._filepicker, "delete_detail_frame"):
            try:
                self._filepicker.delete_detail_frame(self._options_detail_frame_name)
            except Exception:
                pass

        self._options_detail_controller = DetailFrameController(
            glyph=None,
            build_fn=lambda: self._build_options_pane(),
            selection_changed_fn=None,
            filename_changed_fn=None,
            destroy_fn=None,
        )
        self._filepicker.add_detail_frame_from_controller(
            self._options_detail_frame_name,
            self._options_detail_controller,
        )

    def _on_filter_item(self, item: FileBrowserItem) -> bool:
        if not item or item.is_folder:
            return True

        if self._selection_type == FileBrowserSelectionType.DIRECTORY_ONLY:
            return False

        if self._filepicker.current_filter_option >= len(self._filter_regexes):
            return False

        regex = self._filter_regexes[self._filepicker.current_filter_option]
        if regex.match(item.path, re.IGNORECASE):
            return True
        else:
            return False

    def _on_error(self, msg: str):
        pass

    def _on_click_open(self, filepath: str, dirname: str):
        """
        The meat of the App is done in this callback when the user clicks 'Accept'. This is
        a potentially costly operation so we implement it as an async operation.  The inputs
        are the filename and directory name. Together they form the fullpath to the selected
        file.
        """
        if not dirname:
            return

        selection_paths = self._filepicker.get_current_selections()
        if dirname:
            if filepath:
                current_directory_path = self._filepicker.get_current_directory()
                if current_directory_path.endswith("/"):
                    current_directory_path = current_directory_path[:-1]
                current_directory_name = os.path.basename(current_directory_path)
                filename = os.path.basename(filepath)

                # FIXME: It's possible that the file name in the input dialog
                # is the same as the current folder name, which is selected.
                # But FileDialog class will not include folders in selection_paths,
                # so here it's exclude that it's folder selection.
                if not selection_paths and current_directory_name == filename:
                    fullpath = dirname
                else:
                    if not dirname.endswith("/"):
                        dirname = dirname + "/"

                    # To keep back compatibility, fullpath will be in style of
                    # `file:/c:/folder/test.usd` on windows.
                    fullpath = clientutils.make_absolute_url_if_possible(dirname, filepath)
                    # OMFP-1621: Need revert %20 to space
                    fullpath = urllib.parse.unquote(fullpath)

                    # Strips file: prefix.
                    if fullpath.startswith("file:"):
                        fullpath = fullpath[len("file:") :]

                    # If it's windows, trying to strip prefixed forward slash
                    if os.name == "nt" and fullpath[0] == "/":
                        fullpath = fullpath[1:]
            else:
                fullpath = dirname
        else:
            fullpath = filename

        if self._selection_type == FileBrowserSelectionType.FILE_ONLY and not filename:
            return

        if not selection_paths:
            selection_paths = [fullpath]

        if not self._allow_multi_selections:
            result, entry = omni.client.stat(selection_paths[0])
            if result == omni.client.Result.OK and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
                is_folder = True
            else:
                is_folder = False

            if (is_folder and self._selection_type == FileBrowserSelectionType.FILE_ONLY) or (
                not is_folder and self._selection_type == FileBrowserSelectionType.DIRECTORY_ONLY
            ):
                return

        self.hide_dialog()

        if self._custom_select_fn:
            if self._allow_multi_selections and len(selection_paths) > 1:
                self._custom_select_fn(selection_paths)
            else:
                self._custom_select_fn([fullpath])

    def _on_click_cancel(self, filename: str, dirname: str):
        """
        This function is called when the user clicks 'Cancel'.
        """
        self.hide_dialog()

        if self._custom_cancel_fn:
            self._custom_cancel_fn()
