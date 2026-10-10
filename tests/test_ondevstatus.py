"""OnDevStatusCB（C 侧状态查询回调）的锁/按钮状态归一化测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs, FakeHass, FakeState  # noqa: F401
_setup_stubs()


def _setup(hw, router, entity_id, domain, name, state_value):
    hass = FakeHass()
    hass.states.add(FakeState(entity_id, state_value, name=name))
    hw.ghass = hass
    hw.service_router = router
    vd = router.register_direct_entity(
        f"entity::{entity_id}", name,
        [{"entity_id": entity_id, "domain": domain, "name": name}])
    assert vd is not None
    return vd


def test_ondevstatus_lock_unlocked(hw, router):
    vd = _setup(hw, router, "lock.tank300", "lock", "车门锁", "unlocked")
    value = hw.OnDevStatusCB(vd.sn.encode(), b"switch")
    assert value == 1


def test_ondevstatus_lock_locked(hw, router):
    vd = _setup(hw, router, "lock.tank300", "lock", "车门锁", "locked")
    value = hw.OnDevStatusCB(vd.sn.encode(), b"switch")
    assert value == 0


def test_ondevstatus_button_uses_cache(hw, router):
    vd = _setup(hw, router, "button.horn", "button", "鸣笛", "unknown")
    vd.switch_state = 1
    value = hw.OnDevStatusCB(vd.sn.encode(), b"switch")
    assert value == 1
    vd.switch_state = 0
    assert hw.OnDevStatusCB(vd.sn.encode(), b"switch") == 0


def test_ondevstatus_normal_switch(hw, router):
    _setup(hw, router, "switch.pdu_1", "switch", "插座1", "on")
    vd = router.sn_manager.get_by_device_id("entity::switch.pdu_1")
    assert hw.OnDevStatusCB(vd.sn.encode(), b"switch") == 1
