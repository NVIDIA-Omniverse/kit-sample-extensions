from typing import Optional
from unittest.mock import patch

import carb
import omni.kit.test
from omni.kit.ngsearch import NGSearchExtension
from omni.kit.ngsearch.utils import LogLevel, log_message


class TestExtension(omni.kit.test.AsyncTestCase):
    async def test_get_instance(self):
        ext = NGSearchExtension()
        ext.on_startup(ext_id=None)
        self.assertIsNone(ext._client_instance)
        client = ext._client
        self.assertIsNotNone(ext._client_instance)
        self.assertEqual(client, ext._client_instance)
        ext.on_shutdown()
        self.assertIsNone(ext._client_instance)


class TestUtils(omni.kit.test.AsyncTestCase):
    async def test_logging(self):
        level: Optional[LogLevel]
        for level in list(LogLevel) + [None, "invalid"]:
            with self.subTest(search_gen_mock=level.value if isinstance(level, LogLevel) else level):
                with (
                    patch.object(carb, "log_verbose", autospec=True) as mock_carb_log_verbose,
                    patch.object(carb, "log_info", autospec=True) as mock_carb_log_info,
                    patch.object(carb, "log_warn", autospec=True) as mock_carb_log_warn,
                    patch.object(carb, "log_error", autospec=True) as mock_carb_log_error,
                ):
                    log_message("test message", level=level)
                    if level == LogLevel.debug:
                        mock_carb_log_verbose.assert_called_once()
                        mock_carb_log_info.assert_not_called()
                        mock_carb_log_warn.assert_not_called()
                        mock_carb_log_error.assert_not_called()
                    elif level == LogLevel.info:
                        mock_carb_log_verbose.assert_not_called()
                        mock_carb_log_info.assert_called_once()
                        mock_carb_log_warn.assert_not_called()
                        mock_carb_log_error.assert_not_called()
                    elif level == LogLevel.warning:
                        mock_carb_log_verbose.assert_not_called()
                        mock_carb_log_info.assert_not_called()
                        mock_carb_log_warn.assert_called_once()
                        mock_carb_log_error.assert_not_called()
                    elif level == LogLevel.error:
                        mock_carb_log_verbose.assert_not_called()
                        mock_carb_log_info.assert_not_called()
                        mock_carb_log_warn.assert_not_called()
                        mock_carb_log_error.assert_called_once()
                    elif level is None:
                        mock_carb_log_verbose.assert_not_called()
                        mock_carb_log_info.assert_called_once()
                        mock_carb_log_warn.assert_not_called()
                        mock_carb_log_error.assert_not_called()
                    else:
                        mock_carb_log_verbose.assert_not_called()
                        mock_carb_log_info.assert_called_once()
                        mock_carb_log_warn.assert_called_once()
                        mock_carb_log_error.assert_not_called()
