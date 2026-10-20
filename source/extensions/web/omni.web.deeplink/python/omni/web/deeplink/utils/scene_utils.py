import asyncio

import carb
import omni.usd
from pxr import Gf, Vt


class StageEventHandler:
    """A stage event handler class for managing asynchronous stage events in Omni UI.

    This class subscribes to stage event notifications and provides asynchronous mechanisms to wait for a specified stage event. It records stage events and uses futures to signal when the required event is received, allowing the caller to wait for changes in stage status. This is particularly useful for synchronizing operations that depend on stage events in Omni UI.

    Args:
        ext_name (str): The name of the extension associated with the stage event subscription.
    """

    def __init__(self, ext_name):
        """Initializes a StageEventHandler instance."""
        self._future_test = None
        self._required_stage_event = -1
        usd = omni.usd.get_context()
        self._stage_event_sub = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=usd.stage_event_name(omni.usd.StageEventType(i)),
                on_event=lambda _, event_type=i: self._on_stage_event(event_type),
            )
            for i in range(int(omni.usd.StageEventType.COUNT))
        ]

    def _on_stage_event(self, event_type):
        """Handles stage event notifications and triggers futures when the required event is received.

        Args:
            event_type (int): The type of stage event that occurred.
        """
        stage_name = "None"
        if omni.usd.get_context().get_stage() and omni.usd.get_context().get_stage().GetRootLayer():
            stage_name = omni.usd.get_context().get_stage().GetRootLayer().identifier
        if (
            self._future_test
            and (
                int(self._required_stage_event) == event_type
                or int(self._required_stage_event) == omni.usd.StageEventType.OPEN_FAILED
            )
            and not self._future_test.done()
        ):
            self._future_test.set_result(event_type)

    def destroy(self):
        """Cleanup event subscriptions."""
        for sub in self._stage_event_sub:
            sub.reset()
        self._stage_event_sub.clear()

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.destroy()

    async def reset_stage_event(self, stage_event):
        """Resets the internal event waiting mechanism using the specified stage event.

        Args:
            stage_event (int): Stage event identifier to be awaited.
        """
        self._required_stage_event = stage_event
        self._future_test = asyncio.Future()

    async def wait_for_stage_event(self, timeout=None):
        """Waits for the required stage event to occur within the specified timeout.

        Args:
            timeout (float): Maximum waiting time in seconds.
        """

        if timeout is None:
            timeout = carb.settings.get_settings().get_as_float("/exts/omni.web.deeplink/wait_for_stage_event_timeout")

        async def wait_for_event():
            return await self._future_test if self._future_test is not None else None

        try:
            await asyncio.wait_for(wait_for_event(), timeout=timeout)
        except asyncio.TimeoutError:
            carb.log_error(f"wait_for_stage_event timeout waiting for {self._required_stage_event}")
        finally:
            self._future_test = None
            self._required_stage_event = -1


def get_resolved_value(value: str):
    """Convert string to resolved value with proper error handling.

    Parses string representations of various data types including booleans, floats,
    vectors, quaternions, matrices, and arrays into their corresponding Python/USD objects.
    Supports Gf (Graphics Foundation) types like Vec3f, Matrix4d, and Vt (Value Types)
    arrays.

    Args:
        value (str): String representation of the value to be converted.
    """

    def str_to_float_array(value: str):
        return [float(part) for part in value.split(",") if part != ""]

    def str_to_matrix_float_array(value: str):
        parts = value.split(f"), (")
        parts[0] = parts[0].strip()[1:]
        parts[-1] = parts[-1].strip()[:-1]
        values = []
        for part in parts:
            values.extend(str_to_float_array(part))
        return values

    def str_to_string_array(value: str):
        return [str(part) for part in value.split(",") if part != ""]

    type_parsers = {
        "True": lambda v: True,
        "False": lambda v: False,
        "float(": lambda v: float(v),
        "Vec3f(": lambda v: Gf.Vec3f(str_to_float_array(v)),
        "Vec3d(": lambda v: Gf.Vec3d(str_to_float_array(v)),
        "Vec2f(": lambda v: Gf.Vec2f(str_to_float_array(v)),
        "Vec2d(": lambda v: Gf.Vec2d(str_to_float_array(v)),
        "Vec4f(": lambda v: Gf.Vec4f(str_to_float_array(v)),
        "Vec4d(": lambda v: Gf.Vec4d(str_to_float_array(v)),
        "Quatf(": lambda v: Gf.Quatf(str_to_float_array(v)),
        "Quatd(": lambda v: Gf.Quatd(str_to_float_array(v)),
        "Quath(": lambda v: Gf.Quath(str_to_float_array(v)),
        "Vec4fArray(": lambda v: Vt.Vec4fArray(str_to_float_array(v)),
        "TokenArray(": lambda v: Vt.TokenArray(str_to_string_array(v)),
    }

    try:
        if value.startswith('"'):
            return value[1:-1]

        if value.startswith("Matrix3f("):
            values = str_to_matrix_float_array(value[len("Matrix3f(") : -1])
            return Gf.Matrix3f(
                values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7], values[8]
            )

        if value.startswith("Matrix3d("):
            values = str_to_matrix_float_array(value[len("Matrix3d(") : -1])
            return Gf.Matrix3d(
                values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7], values[8]
            )

        if value.startswith("Matrix4f("):
            values = str_to_matrix_float_array(value[len("Matrix4f(") : -1])
            return Gf.Matrix4f(
                values[0],
                values[1],
                values[2],
                values[3],
                values[4],
                values[5],
                values[6],
                values[7],
                values[8],
                values[9],
                values[10],
                values[11],
                values[12],
                values[13],
                values[14],
                values[15],
            )

        if value.startswith("Matrix4d("):
            values = str_to_matrix_float_array(value[len("Matrix4d(") : -1])
            return Gf.Matrix4d(
                values[0],
                values[1],
                values[2],
                values[3],
                values[4],
                values[5],
                values[6],
                values[7],
                values[8],
                values[9],
                values[10],
                values[11],
                values[12],
                values[13],
                values[14],
                values[15],
            )

        for prefix, parser in type_parsers.items():
            if value.startswith(prefix):
                return parser(value[len(prefix) : -1])

        return None
    except (ValueError, IndexError) as e:
        carb.log_error(f"Failed to parse value '{value}': {e}")
        return None
