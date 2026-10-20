# pylint: disable=relative-beyond-top-level,protected-access,no-member
from unittest.mock import MagicMock, patch

import omni.client

from ...scripts.settings import utils
from ...scripts.settings.utils import (
    _get_bool,
    _get_list,
    is_existing_path,
)
from ..base import MaterialGraphTestBase


class TestSettingsUtilsMore(MaterialGraphTestBase):
    """Additional tests for settings utils helpers."""

    async def test_get_bool_coercion(self) -> None:
        """_get_bool should coerce values and honor defaults."""
        fake_settings = MagicMock()
        fake_settings.get.side_effect = [True, 0, None]
        with patch.object(utils.carb.settings, "get_settings", return_value=fake_settings):
            self.assertTrue(_get_bool("k", False))
            self.assertFalse(_get_bool("k", True))
            self.assertTrue(_get_bool("k", True))

    async def test_get_list_coercion(self) -> None:
        """_get_list should coerce strings and ignore unsupported types."""
        fake_settings = MagicMock()
        fake_settings.get.side_effect = [["a"], "b", 5, None]
        with patch.object(utils.carb.settings, "get_settings", return_value=fake_settings):
            self.assertEqual(_get_list("k"), ["a"])
            self.assertEqual(_get_list("k"), ["b"])
            self.assertEqual(_get_list("k"), [])
            self.assertEqual(_get_list("k"), [])

    async def test_is_existing_path_omni_client(self) -> None:
        """is_existing_path should use omni.client for URLs."""
        with patch.object(omni.client, "stat", return_value=(omni.client.Result.OK, None)):
            self.assertTrue(is_existing_path("omniverse://server/path"))

    async def test_is_existing_path_local(self) -> None:
        """is_existing_path should fall back to local path exists."""
        with (
            patch.object(omni.client, "stat", return_value=(omni.client.Result.ERROR_NOT_FOUND, None)),
            patch("pathlib.Path.exists", return_value=True),
        ):
            self.assertTrue(is_existing_path("C:/tmp/path"))
