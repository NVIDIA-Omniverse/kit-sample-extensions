# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import omni.client
import omni.ui as ui


class PropAssetTagsWidget:
    """Class for building and maintaining tags chips"""

    def __init__(self, tags, browser_widget):
        """tag chips

        Args:
            tags (list): list of tags
            browser_widget(get_instance().browser_widget): instance of base browser widget
        """
        self.browser_widget = browser_widget
        self._tags = tags
        self._tag_chips = []
        self._tag_buttons = {}

        self.tag_stack = ui.Frame(spacing=5)
        self._frame_size = 50

        def setFrame():
            self._frame_size = int(self.tag_stack.computed_width / 8)

            self.clear_tags()
            with self.tag_stack:
                self.build_tag_chips()

        self.tag_stack.set_computed_content_size_changed_fn(setFrame)

        with self.tag_stack:
            self.build_tag_chips()

    @property
    def tags(self):
        """Property gor tag values
        Returns:
            List: tag values
        """
        return self._tags

    @tags.setter
    def tags(self, tags):
        """Property Setter for adding tag also rebuilds tags buttons

        Args:
            tags (List): List tag values
        """
        # Remove existing tags in frame
        self.clear_tags()
        # Set Tags Property
        self._tags = tags
        # Rebuild new tags
        with self.tag_stack:
            self.build_tag_chips()

    def clear_tags(self):
        """clears all tag button in the frame"""
        self.tag_stack.clear()

    def append_tag(self, tag):
        """Add a tag value to the existing tag list. Check for doubles"""
        if tag not in self.tags:
            add_tag = self.tag.append(tag)
            self._tag = add_tag

    def remove_chip(self, chip):
        """Remove this chip from the ui"""
        for c in chip:
            c.visible = False

    def build_tag_chips(self):
        """Build the tag chip ui and added link function to Browser Search Bar"""

        def on_click(value):
            """set the browse search field with this tag

            Args:
                value (str): tag search value
            """
            search_field = self.browser_widget.search_field
            search_field.search_words = [value]

        row_list = []
        row_count = 0
        char_count = 0
        list_of_rows = []

        # each index is a list of tags that will fit in the row based on the size of the frame.
        for t in self.tags:
            new_chars = char_count + len(t)
            if new_chars < self._frame_size:
                row_list.append(t)
                char_count = new_chars
            else:
                list_of_rows.append(row_list)
                row_list = []
                row_list.append(t)
                char_count = len(t)

        list_of_rows.append(row_list)
        # build the buttons
        with ui.VGrid(padding=5, row_height=30):
            for row in list_of_rows:
                with ui.HStack(spacing=5):
                    for r in row:
                        new_button = ui.Button(r, clicked_fn=on_click, height=0, width=0)
                        new_button.set_clicked_fn(lambda value=r: on_click(value))
