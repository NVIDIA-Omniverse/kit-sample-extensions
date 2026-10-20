import fnmatch

import carb
import omni.kit.app
from carb.eventdispatcher import Event, get_eventdispatcher


def matched_patterns(s: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if fnmatch.fnmatch(s, p)]


def match(s: str, patterns: list[str]) -> bool:
    return len(matched_patterns(s, patterns)) > 0


def escape_for_fnmatch(s: str) -> str:
    return s.replace("[", "[[]")


EXCLUDE = [
    "*[omni.usd] failed to get rt interface*",
    "*[omni.fabric.plugin] Could not load any plugins to populate Fabric*",
    "*[omni.usd] '/app/useFabricSceneDelegate' is enabled, but usdrt::population::IUtils could not be created. Is UsdRt enabled?*",
]


class LogErrorChecker:
    """Automatically subscribes to logging events and monitors if error were produced during the test."""

    def __init__(self):
        # Setup this test case to fail if any error is produced
        self._exclude = [escape_for_fnmatch(s.lower()) for s in EXCLUDE]
        self._error_count = 0

        def on_log_event(e: Event):
            if e["level"] >= carb.logging.LEVEL_ERROR:
                line = "[{}] {}".format(e["source"], e["message"]).lower()
                if not match(line, self._exclude):
                    self._error_count = self._error_count + 1

        self._log_sub = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_ERROR_LOG_IMMEDIATE,
            on_event=on_log_event,
            observer_name="test log event",
        )

    def shutdown(self):
        self._log_sub = None

    def get_error_count(self):
        return self._error_count
