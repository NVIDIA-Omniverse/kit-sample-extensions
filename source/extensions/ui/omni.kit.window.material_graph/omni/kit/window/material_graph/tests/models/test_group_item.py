# pylint: disable=relative-beyond-top-level,no-member
from ...scripts.models.catalog.core.base import BaseItem
from ...scripts.models.catalog.items.group import GroupItem
from ..base import MaterialGraphTestBase


class _TaggedItem(BaseItem):
    """BaseItem with tags and context visibility."""

    def __init__(self, name: str, tags=None, visible=True) -> None:
        super().__init__(name, "", "", "")
        self.tags = tags or []
        self._visible = visible

    def is_visible_in_context(self, _context: str) -> bool:
        return self._visible


class TestGroupItem(MaterialGraphTestBase):
    """Tests for GroupItem behaviors."""

    async def test_add_child_sorts(self) -> None:
        """Children should be sorted by name."""
        group = GroupItem("Group")
        group.add_child(BaseItem("b", "", "", ""))
        group.add_child(BaseItem("a", "", "", ""))
        self.assertEqual([child.name for child in group.children], ["a", "b"])

    async def test_prefilter_respects_tags_and_visibility(self) -> None:
        """prefilter should use tags and context visibility."""
        group = GroupItem("Group")
        group.add_child(_TaggedItem("one", tags=["foo"]))
        group.add_child(_TaggedItem("two", tags=["bar"], visible=False))

        group.prefilter("foo", current_context="mdl")
        self.assertTrue(group.filtered)
        self.assertTrue(group.children[0].filtered)
        self.assertFalse(group.children[1].filtered)
