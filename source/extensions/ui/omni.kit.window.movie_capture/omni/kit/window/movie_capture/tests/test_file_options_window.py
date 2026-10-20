import omni.kit.test
from omni.kit.window.movie_capture.file_options import FileOptions
from omni.kit.window.movie_capture.ui.file_options_window import FileOptionsWindow


class TestFileOptionsWindow(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        self._file_options_window = FileOptionsWindow()
        self._file_options = FileOptions()

    async def test_pass_valid_options_default(self):
        self._file_options_window.show(self._file_options)
        await omni.kit.app.get_app().next_update_async()

        self._file_options_window._on_apply_clicked()
        await omni.kit.app.get_app().next_update_async()

        file_options_returned = self._file_options_window.get_options()
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_FILE_TYPE, None), ".png")
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_COMM_SAVE_ALPHA, None), False)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_HDR_OUTPUT, None), False)
        self.assertEqual(
            file_options_returned.get_option(FileOptions.OPTION_EXR_COMP_METHOD, None),
            FileOptions.DEFAULT_EXR_COPM_METHOD,
        )

    async def test_pass_valid_options_customized(self):
        self._file_options.set_option(FileOptions.OPTION_FILE_TYPE, ".png")
        self._file_options.set_option(FileOptions.OPTION_COMM_SAVE_ALPHA, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_HDR_OUTPUT, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_COMP_METHOD, "dwaa")

        self._file_options_window.show(self._file_options)
        await omni.kit.app.get_app().next_update_async()

        self._file_options_window._on_apply_clicked()
        await omni.kit.app.get_app().next_update_async()

        file_options_returned = self._file_options_window.get_options()
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_FILE_TYPE, None), ".png")
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_COMM_SAVE_ALPHA, None), True)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_HDR_OUTPUT, None), True)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_COMP_METHOD, None), "dwaa")

    async def test_pass_invalid_exr_comp_method_option(self):
        self._file_options.set_option(FileOptions.OPTION_FILE_TYPE, ".png")
        self._file_options.set_option(FileOptions.OPTION_COMM_SAVE_ALPHA, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_HDR_OUTPUT, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_COMP_METHOD, "non-exist")

        self._file_options_window.show(self._file_options)
        await omni.kit.app.get_app().next_update_async()

        self._file_options_window._on_apply_clicked()
        await omni.kit.app.get_app().next_update_async()

        file_options_returned = self._file_options_window.get_options()
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_FILE_TYPE, None), ".png")
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_COMM_SAVE_ALPHA, None), True)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_HDR_OUTPUT, None), True)
        self.assertEqual(
            file_options_returned.get_option(FileOptions.OPTION_EXR_COMP_METHOD, None),
            FileOptions.DEFAULT_EXR_COPM_METHOD,
        )

    async def test_cancel_doesnt_change_options(self):
        self._file_options.set_option(FileOptions.OPTION_FILE_TYPE, ".png")
        self._file_options.set_option(FileOptions.OPTION_COMM_SAVE_ALPHA, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_HDR_OUTPUT, True)
        self._file_options.set_option(FileOptions.OPTION_EXR_COMP_METHOD, "rle")

        self._file_options_window.show(self._file_options)
        await omni.kit.app.get_app().next_update_async()

        self._file_options_window._ui_exr_cm_radio_collection.model.as_int = 0
        await omni.kit.app.get_app().next_update_async()
        self._file_options_window._ui_save_alpha_check.model.as_bool = False
        await omni.kit.app.get_app().next_update_async()
        self._file_options_window._ui_hdr_output_check.model.as_bool = False
        await omni.kit.app.get_app().next_update_async()
        self._file_options_window._on_cancel_clicked()
        await omni.kit.app.get_app().next_update_async()

        file_options_returned = self._file_options_window.get_options()
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_FILE_TYPE, None), ".png")
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_COMM_SAVE_ALPHA, None), True)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_HDR_OUTPUT, None), True)
        self.assertEqual(file_options_returned.get_option(FileOptions.OPTION_EXR_COMP_METHOD, None), "rle")
