"""Headless coverage for InputNode context classification and grouping."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import omni.kit.test

from ...scripts.models.graph import input_node_view as input_view_module
from ...scripts.models.graph.input_node_view import (
    InputNodeViewMode,
    InputNodeViewModel,
    IoState,
    _PortGroup,
    _SyntheticGroupHeader,
)


class _Port:
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name


class _Lookup:
    def __init__(self, values) -> None:
        self.values = values

    def __getitem__(self, item):
        value = self.values[item]
        if isinstance(value, Exception):
            raise value
        return value


class TestInputNodeViewModel(omni.kit.test.AsyncTestCase):
    """Exercise InputNode view modes without native canvas or UI events."""

    async def test_initial_state_modes_group_helpers_and_synthetic_header(self) -> None:
        model = InputNodeViewModel()
        self.assertEqual(model.mode, InputNodeViewMode.CURRENT_CONTEXT)
        self.assertFalse(model.has_active_ports)
        self.assertEqual(model.total_port_count, 0)
        self.assertIsNone(model.empty_port)
        self.assertEqual(model.get_ordered_port_entries(), [])
        self.assertEqual(model.cycle_mode(), InputNodeViewMode.ALL_USED)
        self.assertEqual(model.cycle_mode(), InputNodeViewMode.ALL_PORTS)
        self.assertEqual(model.cycle_mode(), InputNodeViewMode.CURRENT_CONTEXT)
        model.mode = InputNodeViewMode.ALL_PORTS
        self.assertEqual(model.mode, InputNodeViewMode.ALL_PORTS)

        first, second, third = _Port("first"), _Port("second"), _Port("third")
        group = _PortGroup("Group")
        group.ports = [(third, IoState.UNUSED), (second, IoState.USED_IN_OTHER), (first, IoState.ACTIVE_IN_CURRENT)]
        self.assertEqual(group.count, 3)
        self.assertTrue(group.has_active())
        self.assertTrue(group.has_used())
        group.sort_ports()
        self.assertEqual([port for port, _state in group.ports], [first, second, third])

        header = _SyntheticGroupHeader("Group", 3, True, IoState.USED_IN_OTHER)
        self.assertEqual((header.name, header.port_count, header.collapsed), ("Group", 3, True))
        self.assertEqual(header.io_state_summary, IoState.USED_IN_OTHER)

    async def test_rebuild_from_ports_resets_state_and_runs_all_phases(self) -> None:
        model = InputNodeViewModel()
        first, second, empty = _Port("first"), _Port("second"), object()
        input_node = SimpleNamespace(source=SimpleNamespace(prim="root-prim"), empty_port=empty)
        model._classify_all = MagicMock()
        model._extract_display_groups = MagicMock()
        model._build_groups = MagicMock()
        model._io_states[99] = IoState.UNUSED
        model._port_contexts[99] = ["old"]
        model._display_groups[99] = "old"
        model._groups.append(_PortGroup("old"))

        model.rebuild_from_ports(input_node, [first, second], "isolation", "mtlx", "manager")
        self.assertTrue(model._built)
        self.assertEqual(model._current_context, "mtlx")
        self.assertEqual(model._all_ports, [first, second])
        self.assertIs(model.empty_port, empty)
        model._classify_all.assert_called_once_with([first, second], "isolation", "root-prim", "mtlx", "manager")
        model._extract_display_groups.assert_called_once_with([first, second], "isolation")
        model._build_groups.assert_called_once_with([first, second])

    async def test_classification_distinguishes_active_other_and_unused(self) -> None:
        model = InputNodeViewModel()
        active, other, unused = _Port("active"), _Port("other"), _Port("unused")
        proxies = {
            active: SimpleNamespace(name="active", inputs=[object()], outputs=[]),
            other: SimpleNamespace(name="other", inputs=[], outputs=[]),
            unused: SimpleNamespace(name="unused", inputs=[], outputs=[]),
        }
        isolation = _Lookup(proxies)
        model._has_usd_connections = MagicMock(side_effect=lambda port, *_args: port is other)
        model._discover_contexts = MagicMock(return_value=["mdl"])
        model._classify_all([active, other, unused], isolation, "root", "mtlx", "manager")
        self.assertEqual(model.get_io_state(active), IoState.ACTIVE_IN_CURRENT)
        self.assertEqual(model.get_port_contexts(active), ["mtlx"])
        self.assertEqual(model.get_io_state(other), IoState.USED_IN_OTHER)
        self.assertEqual(model.get_port_contexts(other), ["mdl"])
        self.assertEqual(model.get_io_state(unused), IoState.UNUSED)
        self.assertEqual(model.get_port_contexts(unused), [])
        self.assertTrue(model.has_active_ports)

    async def test_active_and_usd_connection_detection_are_exception_safe(self) -> None:
        port = _Port("value")
        connected = _Lookup({port: SimpleNamespace(inputs=[], outputs=[object()])})
        self.assertTrue(InputNodeViewModel._is_active_in_current(port, connected))
        root_connected = SimpleNamespace(_root_inputs={port: [object()]}, _root_outputs={})
        root_connected.__getitem__ = MagicMock(side_effect=RuntimeError("injected"))
        self.assertTrue(InputNodeViewModel._is_active_in_current(port, root_connected))
        self.assertFalse(InputNodeViewModel._is_active_in_current(port, _Lookup({port: RuntimeError("bad")})))

        attr = SimpleNamespace(IsValid=lambda: True)
        root_prim = SimpleNamespace(GetAttribute=MagicMock(return_value=attr))
        proxy = SimpleNamespace(proxy_attribute=SimpleNamespace(name="inputs:value"))
        isolation = _Lookup({port: proxy})
        usd_input = SimpleNamespace(GetConnectedSources=lambda: ([object()], []))
        with patch.object(input_view_module.UsdShade, "Input", return_value=usd_input):
            self.assertTrue(InputNodeViewModel._has_usd_connections(port, root_prim, isolation))
        self.assertFalse(InputNodeViewModel._has_usd_connections(port, None, isolation))
        root_prim.GetAttribute.side_effect = RuntimeError("injected")
        self.assertFalse(InputNodeViewModel._has_usd_connections(port, root_prim, isolation))

    async def test_context_discovery_and_display_group_normalization(self) -> None:
        handles = {
            "current": SimpleNamespace(is_valid=True),
            "mdl": SimpleNamespace(is_valid=True),
            "invalid": SimpleNamespace(is_valid=False),
        }
        manager = SimpleNamespace(
            get_context_names=lambda: list(handles),
            get_context=lambda name: handles[name],
        )
        self.assertEqual(InputNodeViewModel._discover_contexts(object(), manager, "current", object()), ["mdl"])
        broken = SimpleNamespace(get_context_names=MagicMock(side_effect=RuntimeError("injected")))
        self.assertEqual(InputNodeViewModel._discover_contexts(object(), broken, "current", object()), ["other"])

        first, second, third, fourth = (_Port(str(index)) for index in range(4))
        isolation = _Lookup(
            {
                first: SimpleNamespace(display_group="Inputs:Surface:Advanced"),
                second: SimpleNamespace(display_group="Inputs"),
                third: SimpleNamespace(display_group="Geometry"),
                fourth: RuntimeError("injected"),
            }
        )
        model = InputNodeViewModel()
        model._extract_display_groups([first, second, third, fourth], isolation)
        self.assertEqual(model._display_groups[id(first)], "Surface")
        self.assertEqual(model._display_groups[id(second)], "")
        self.assertEqual(model._display_groups[id(third)], "Geometry")
        self.assertEqual(model._display_groups[id(fourth)], "")

    async def test_group_building_orders_active_and_honors_collapse_overrides(self) -> None:
        active, used, unused = _Port("active"), _Port("used"), _Port("unused")
        model = InputNodeViewModel()
        model._io_states = {
            id(active): IoState.ACTIVE_IN_CURRENT,
            id(used): IoState.USED_IN_OTHER,
            id(unused): IoState.UNUSED,
        }
        model._display_groups = {
            id(active): "Surface",
            id(used): "Geometry",
            id(unused): "Surface",
        }
        model._group_collapse_overrides = {"Surface": True, "Geometry": False}
        model._build_groups([unused, used, active])
        self.assertEqual([group.name for group in model._groups], ["Surface", "Geometry"])
        self.assertTrue(model._groups[0].collapsed)
        self.assertFalse(model._groups[1].collapsed)
        self.assertEqual([port for port, _state in model._groups[0].ports], [active, unused])

        model.toggle_group_collapsed("Surface")
        self.assertFalse(model._group_collapse_overrides["Surface"])
        model.toggle_group_collapsed("Missing")

    async def test_large_ungrouped_port_sets_force_split_and_keep_one_open(self) -> None:
        ports = [_Port(f"port{index:02}") for index in range(21)]
        model = InputNodeViewModel()
        model._io_states = {id(port): IoState.UNUSED for port in ports}
        model._display_groups = {id(port): "" for port in ports}
        fallback = model._fallback_groups(ports)
        self.assertEqual(list(fallback), ["General"])
        self.assertEqual(fallback["General"].count, 21)

        split = model._force_split(fallback["General"])
        self.assertGreater(len(split), 1)
        self.assertFalse(split[0].collapsed)
        self.assertEqual(sum(group.count for group in split), 21)
        model._build_groups(ports)
        self.assertGreater(len(model._groups), 1)
        self.assertFalse(model._groups[0].collapsed)

    async def test_ordered_entries_cover_all_modes_grouping_and_empty_port(self) -> None:
        active, other, unused, empty = (_Port(name) for name in ("active", "other", "unused", "empty"))
        first = _PortGroup("First")
        first.ports = [(active, IoState.ACTIVE_IN_CURRENT), (other, IoState.USED_IN_OTHER)]
        second = _PortGroup("Second")
        second.ports = [(unused, IoState.UNUSED)]
        model = InputNodeViewModel()
        model._built = True
        model._groups = [first, second]
        model._all_ports = [active, other, unused]
        model._empty_port = empty

        model.mode = InputNodeViewMode.CURRENT_CONTEXT
        current = model.get_ordered_port_entries()
        self.assertIsInstance(current[0], _SyntheticGroupHeader)
        self.assertIn((active, IoState.ACTIVE_IN_CURRENT), current)
        self.assertIsInstance(current[-2], _SyntheticGroupHeader)
        self.assertEqual(current[-1], (empty, -1))

        model.mode = InputNodeViewMode.ALL_USED
        used = model.get_ordered_port_entries()
        self.assertIn((active, IoState.ACTIVE_IN_CURRENT), used)
        self.assertIn((other, IoState.USED_IN_OTHER), used)
        self.assertNotIn((unused, IoState.UNUSED), used)

        model.mode = InputNodeViewMode.ALL_PORTS
        all_ports = model.get_ordered_port_entries()
        self.assertIn((unused, IoState.UNUSED), all_ports)
        self.assertEqual(model._visible_in_group(first, InputNodeViewMode.CURRENT_CONTEXT), [(active, 0)])
        self.assertEqual(len(model._visible_in_group(first, InputNodeViewMode.ALL_USED)), 2)
        self.assertEqual(len(model._visible_in_group(first, InputNodeViewMode.ALL_PORTS)), 2)

    async def test_rebuild_and_group_collapse_fail_safe_boundaries(self) -> None:
        """Standalone rebuild delegates authoritative ports and collapse toggles remain stable."""
        model = InputNodeViewModel()
        ports = [_Port("a"), _Port("b")]
        input_node = SimpleNamespace(source=object(), ports=ports, empty_port=None)
        model.rebuild_from_ports = MagicMock()
        model.rebuild(input_node, "isolation", "mdl", "manager")
        model.rebuild_from_ports.assert_called_once_with(input_node, ports, "isolation", "mdl", "manager")

        group = _PortGroup("Group")
        group.collapsed = True
        model._groups = [group]
        model.toggle_group_collapsed("Group")
        self.assertFalse(model._group_collapse_overrides["Group"])
        model.toggle_group_collapsed("Group")
        self.assertTrue(model._group_collapse_overrides["Group"])

    async def test_collapsed_entry_builders_keep_a_usable_active_group(self) -> None:
        """Grouped modes preserve summaries while ensuring current active ports can be reached."""
        active = _Port("active")
        other = _Port("other")
        unused = _Port("unused")
        first = _PortGroup("First")
        first.ports = [(active, IoState.ACTIVE_IN_CURRENT), (other, IoState.USED_IN_OTHER)]
        first.collapsed = True
        empty = _PortGroup("Empty")
        empty.ports = []
        second = _PortGroup("Second")
        second.ports = [(unused, IoState.UNUSED)]
        second.collapsed = True

        model = InputNodeViewModel()
        model._groups = [first, empty, second]
        model._group_collapse_overrides = {"First": True, "Second": False}
        current = model._entries_current_context(True)
        self.assertIsInstance(current[0], _SyntheticGroupHeader)
        self.assertFalse(current[0].collapsed)
        self.assertIn((active, IoState.ACTIVE_IN_CURRENT), current)
        self.assertTrue(current[-1].collapsed)

        used = model._entries_all_used(True)
        self.assertIsInstance(used[0], _SyntheticGroupHeader)
        self.assertNotIn((unused, IoState.UNUSED), used)
        all_ports = model._entries_all_ports(True)
        self.assertNotIn("Empty", [entry.name for entry in all_ports if isinstance(entry, _SyntheticGroupHeader)])
        self.assertIn((unused, IoState.UNUSED), all_ports)

    async def test_group_policy_and_connection_fallback_edges(self) -> None:
        """Small and large groups stay usable while malformed connection proxies fail closed."""
        active = _Port("active")
        model = InputNodeViewModel()
        model._io_states = {id(active): IoState.ACTIVE_IN_CURRENT}
        model._display_groups = {id(active): "Surface"}
        model._build_groups([active])
        self.assertFalse(model._groups[0].collapsed)

        many_active = [_Port(f"active{index:02}") for index in range(10)]
        model._io_states = {id(port): IoState.ACTIVE_IN_CURRENT for port in many_active}
        model._display_groups = {id(port): "Surface" for port in many_active}
        model._build_groups(many_active)
        self.assertFalse(model._groups[0].collapsed)

        many_unused = [_Port(f"unused{index:02}") for index in range(30)]
        split_source = _PortGroup("Large")
        split_source.ports = [(port, IoState.UNUSED) for port in many_unused]
        split = model._force_split(split_source)
        self.assertFalse(split[0].collapsed)

        group = _PortGroup("Flat")
        group.ports = [(active, IoState.ACTIVE_IN_CURRENT), (many_unused[0], IoState.UNUSED)]
        model._groups = [group]
        self.assertIn((active, IoState.ACTIVE_IN_CURRENT), model._entries_current_context(False))
        self.assertIn((active, IoState.ACTIVE_IN_CURRENT), model._entries_all_used(False))
        self.assertEqual(len(model._entries_all_ports(False)), 2)

        broken = _Lookup({active: RuntimeError("injected")})
        model._has_usd_connections = MagicMock(return_value=False)
        model._classify_all([active], broken, object(), "mdl", object())
        self.assertEqual(model.get_io_state(active), IoState.UNUSED)

        no_proxy = _Lookup({active: SimpleNamespace(proxy_attribute=None)})
        self.assertFalse(InputNodeViewModel._has_usd_connections(active, object(), no_proxy))
        invalid_attr = SimpleNamespace(IsValid=lambda: False)
        root = SimpleNamespace(GetAttribute=lambda _name: invalid_attr)
        proxy = _Lookup({active: SimpleNamespace(proxy_attribute=SimpleNamespace(name="inputs:active"))})
        self.assertFalse(InputNodeViewModel._has_usd_connections(active, root, proxy))

        class _BrokenIsolation:
            def __getitem__(self, _port):
                raise RuntimeError("injected")

            @property
            def _root_inputs(self):
                raise RuntimeError("injected")

        self.assertFalse(InputNodeViewModel._is_active_in_current(active, _BrokenIsolation()))
