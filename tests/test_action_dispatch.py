"""ServiceActionDispatcher domain 感知分发测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs  # noqa: F401
_setup_stubs()

from custom_components.hwhomebridge.service_action import ServiceActionDispatcher


class RecordingDispatcher(ServiceActionDispatcher):
    """记录 service 调用而非真正执行"""

    def __init__(self):
        super().__init__(hass=object())  # 非 None 即可通过守卫
        self.calls = []

    def _call_service_async(self, domain, service, entity_id, data=None):
        self.calls.append((domain, service, entity_id, data or {}))


def _dispatch(action, entity_id, payload):
    dispatcher = RecordingDispatcher()
    ok = action(dispatcher, entity_id, payload)
    return dispatcher, ok


def test_lock_unlock_on():
    d, ok = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "lock.tank300", {"on": 1})
    assert ok
    assert d.calls == [("lock", "unlock", "lock.tank300", {})]


def test_lock_lock_off():
    d, ok = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "lock.tank300", {"on": 0})
    assert ok
    assert d.calls == [("lock", "lock", "lock.tank300", {})]


def test_button_press_on():
    d, ok = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "button.tank300_horn", {"on": 1})
    assert ok
    assert d.calls == [("button", "press", "button.tank300_horn", {})]


def test_button_press_off():
    d, ok = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "button.cooker_cancel", {"on": 0})
    assert ok
    assert d.calls == [("button", "press", "button.cooker_cancel", {})]


def test_scene_on_and_off_ignored():
    d, ok = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "scene.movie_night", {"on": 1})
    assert ok
    assert d.calls == [("scene", "turn_on", "scene.movie_night", {})]

    d2, ok2 = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                        "scene.movie_night", {"on": 0})
    assert ok2
    assert d2.calls == []  # scene 没有 turn_off


def test_script_on_and_off():
    d, _ = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                     "script.leave_home", {"on": 1})
    assert d.calls == [("script", "turn_on", "script.leave_home", {})]

    d2, _ = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "script.leave_home", {"on": 0})
    assert d2.calls == [("script", "turn_off", "script.leave_home", {})]


def test_generic_switch_domains():
    d, _ = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                     "switch.pdu_1", {"on": 1})
    assert d.calls == [("switch", "turn_on", "switch.pdu_1", {})]

    d2, _ = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "input_boolean.night_mode", {"on": 0})
    assert d2.calls == [("input_boolean", "turn_off",
                         "input_boolean.night_mode", {})]

    d3, _ = _dispatch(ServiceActionDispatcher._handle_turn_on_off,
                      "siren.alarm", {"on": 1})
    assert d3.calls == [("siren", "turn_on", "siren.alarm", {})]
