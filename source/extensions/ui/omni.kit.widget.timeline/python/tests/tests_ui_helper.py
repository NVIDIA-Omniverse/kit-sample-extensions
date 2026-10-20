from unittest.mock import Mock, patch

import omni.kit.app
import omni.kit.test

from ..scripts.ui_helpers import *


class TestResizeableWidget(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_resizeable_widget(self):
        widget = ResizeableWidget(ui.CollapsableFrame("test"))
        widget.set_mouse_fn(Mock())
        widget.update()
        widget.set_begin(1)
        self.assertEqual(widget.get_begin(), 1)
        widget.set_end(2)
        self.assertEqual(widget.get_end(), 2)
        widget.set_width(5, True)
        self.assertEqual(widget.get_width(), 5)
        widget.set_selected(True)
        self.assertTrue(widget.is_selected)
        widget.set_range(2, 3)
        self.assertEqual(widget.get_begin(), 2)
        self.assertEqual(widget.get_end(), 3)
        widget.build_ui()
        widget.update_ui()
        with self.assertRaises(Exception):
            widget._build_ui()
        with self.assertRaises(Exception):
            widget._update_ui()
        self.assertEqual(widget.get_left_handle_style(), "")
        self.assertEqual(widget.get_right_handle_style(), "")

        # simulate the movement of the widget
        widget._begin_moved(widget.left_handle, widget.body, widget.right_handle, widget.body_rectangle)
        widget._body_moved(widget.left_handle, widget.body, widget.right_handle, widget.body_rectangle)
        widget._end_moved(widget.left_handle, widget.body, widget.right_handle, widget.body_rectangle)

        widget = None


class TestMouseClickSorter(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_mouse_click_sorter(self):
        sorter = MouseClickSorter.instance()
        mock1 = Mock()
        mock2 = Mock()
        sorter.add_click_event(mock1, 1)
        sorter.add_click_event(mock2, 2)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        # make sure only first click functon is called
        mock1.assert_called_once()
        mock2.assert_not_called()


class TestProgressPopup(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_progress_popup(self):
        progress = ProgressPopup("test")
        with progress:
            self.assertTrue(progress.is_visible())
        self.assertFalse(progress.is_visible())

        progress.set_progress(0.5)
        self.assertAlmostEqual(progress.get_progress(), 0.5)

        progress.set_status_text("test")
        self.assertEqual(progress.get_status_text(), "test")

        progress.show()
        self.assertTrue(progress.is_visible())

        progress.hide()
        self.assertFalse(progress.is_visible())

        progress = None
