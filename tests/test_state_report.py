"""状态上报与查询的状态归一化测试（lock/button）"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs, FakeState  # noqa: F401
_setup_stubs()

from custom_components.hwhomebridge.service_action import ServiceActionDispatcher


class RecordingDispatcher(ServiceActionDispatcher):
    def __init__(self):
        super().__init__(hass=object())
        self.calls = []

    def _call_service_async(self, domain, service, entity_id, data=None):
        self.calls.append((domain, service, entity_id, data or {}))


def _register(router, entity_id, domain, name="测试"):
    vd = router.register_direct_entity(
        f"entity::{entity_id}", name,
        [{"entity_id": entity_id, "domain": domain, "name": name}])
    assert vd is not None
    return vd


def _capture_reports(router, monkeypatch):
    captured = []
    router._lib = object()  # truthy，允许上报
    monkeypatch.setattr(router, "_update_hw_bridge_status",
                        lambda sn, svcid, payload: captured.append((sn, svcid, payload)))
    return captured


def test_report_lock_state_normalization(router, monkeypatch):
    vd = _register(router, "lock.tank300", "lock", "车门锁")
    captured = _capture_reports(router, monkeypatch)
    svc_def = vd.product.services["switch"]

    router._report_by_type(vd.sn, "switch", svc_def, FakeState("lock.tank300", "unlocked"))
    router._report_by_type(vd.sn, "switch", svc_def, FakeState("lock.tank300", "locked"))

    values = [payload["on"] for _, _, payload in captured]
    assert values == [1, 0]


def test_report_button_state_always_off(router, monkeypatch):
    vd = _register(router, "button.horn", "button", "鸣笛")
    captured = _capture_reports(router, monkeypatch)
    svc_def = vd.product.services["switch"]

    router._report_by_type(vd.sn, "switch", svc_def,
                           FakeState("button.horn", "2026-10-11T00:00:00+00:00"))
    assert captured[-1][2] == {"on": 0}


def test_report_normal_switch(router, monkeypatch):
    vd = _register(router, "switch.pdu_1", "switch", "插座1")
    captured = _capture_reports(router, monkeypatch)
    svc_def = vd.product.services["switch"]

    router._report_by_type(vd.sn, "switch", svc_def, FakeState("switch.pdu_1", "on"))
    router._report_by_type(vd.sn, "switch", svc_def, FakeState("switch.pdu_1", "off"))
    values = [payload["on"] for _, _, payload in captured]
    assert values == [1, 0]


def test_char_state_lock(router):
    vd = _register(router, "lock.tank300", "lock", "车门锁")
    svc_def = vd.product.services["switch"]

    result = router._build_char_state_json(
        "switch", svc_def, FakeState("lock.tank300", "unlocked"), "lock.tank300", vd)
    assert json.loads(result) == {"on": 1}

    result = router._build_char_state_json(
        "switch", svc_def, FakeState("lock.tank300", "locked"), "lock.tank300", vd)
    assert json.loads(result) == {"on": 0}


def test_route_action_button_momentary_state(router):
    """华为 on=1 触发 press 后，瞬时状态缓存置 1（供 C 侧查询）"""
    vd = _register(router, "button.horn", "button", "鸣笛")
    recorder = RecordingDispatcher()
    router.action_dispatcher = recorder
    router._hass = None  # 跳过复位调度

    ok = router.route_action(vd.sn, json.dumps({"on": 1}))

    assert ok
    assert recorder.calls == [("button", "press", "button.horn", {})]
    assert vd.switch_state == 1


def test_route_action_switch_no_momentary(router):
    vd = _register(router, "switch.pdu_1", "switch", "插座1")
    recorder = RecordingDispatcher()
    router.action_dispatcher = recorder
    router._hass = None

    ok = router.route_action(vd.sn, json.dumps({"on": 1}))

    assert ok
    assert recorder.calls == [("switch", "turn_on", "switch.pdu_1", {})]
    assert vd.switch_state == 0
