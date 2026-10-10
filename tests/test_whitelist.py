"""白名单机制测试：注册/注销/持久化/排除回归"""

import json
from pathlib import Path

from conftest import FakeHass, FakeEntityEntry, FakeEntityRegistry, FakeState

from custom_components.hwhomebridge.virtual_device import SNManager


def _prepare_hass(monkeypatch, entities):
    """构造带实体注册表替身的 FakeHass（er.async_get 按 monkeypatch 恢复）"""
    hass = FakeHass()
    reg = FakeEntityRegistry()
    for entity_id, domain, name in entities:
        reg.add(FakeEntityEntry(entity_id, domain, original_name=name))
        hass.states.add(FakeState(entity_id, "off", name=name or entity_id))

    from custom_components.hwhomebridge import hwbridge
    monkeypatch.setattr(hwbridge.er, "async_get", lambda h: reg)
    return hass


def test_whitelist_add_and_register(hw, router, monkeypatch):
    hass = _prepare_hass(monkeypatch, [("lock.tank300", "lock", "车门锁")])
    hw.ghass = hass
    hw.service_router = router

    ok = hw._add_whitelist_entity("lock.tank300")

    assert ok
    assert "lock.tank300" in hw._entity_whitelist
    pseudo = "entity::lock.tank300"
    assert pseudo in hw.registered_device_ids
    assert "lock.tank300" in hw._entity_claimed_entities
    vd = router.sn_manager.get_by_device_id(pseudo)
    assert vd is not None
    assert vd.product.pid == "008"
    assert vd.get_entity_for_service("switch") == "lock.tank300"
    # 白名单持久化
    data = json.loads(Path(hw._entity_whitelist_file).read_text(encoding="utf-8"))
    assert data["entities"] == ["lock.tank300"]


def test_non_whitelisted_entity_not_registered(hw, router, monkeypatch):
    hass = _prepare_hass(monkeypatch, [("lock.other", "lock", "锁")])
    hw.ghass = hass
    hw.service_router = router

    ok = hw._register_single_entity_device("lock.other")
    assert ok is False
    assert router.sn_manager.get_by_device_id("entity::lock.other") is None


def test_unsupported_domain_rejected(hw, router, monkeypatch):
    hass = _prepare_hass(monkeypatch, [("sensor.temp", "sensor", "温度")])
    hw.ghass = hass
    hw.service_router = router
    hw._entity_whitelist.add("sensor.temp")

    ok = hw._register_single_entity_device("sensor.temp")
    assert ok is False
    assert router.sn_manager.get_by_device_id("entity::sensor.temp") is None


def test_excluded_sn_registers_to_snmanager_only(hw, router, monkeypatch):
    """排除列表中的设备只进 SNManager、不上云（设备管理页取消勾选语义）"""
    hass = _prepare_hass(monkeypatch, [("lock.tank300", "lock", "车门锁")])
    hw.ghass = hass
    hw.service_router = router
    hw._entity_whitelist.add("lock.tank300")
    expected_sn = SNManager.generate_sn("entity::lock.tank300")
    hw._excluded_device_sns.add(expected_sn)

    ok = hw._add_whitelist_entity("lock.tank300")

    assert ok
    vd = router.sn_manager.get_by_device_id("entity::lock.tank300")
    assert vd is not None
    assert vd.online is False
    assert "entity::lock.tank300" not in hw.registered_device_ids


def test_remove_whitelist_entity(hw, router, monkeypatch):
    hass = _prepare_hass(monkeypatch, [("lock.tank300", "lock", "车门锁")])
    hw.ghass = hass
    hw.service_router = router
    hw._add_whitelist_entity("lock.tank300")
    assert router.sn_manager.get_by_device_id("entity::lock.tank300") is not None

    hw._remove_whitelist_entity("lock.tank300")

    assert "lock.tank300" not in hw._entity_whitelist
    assert router.sn_manager.get_by_device_id("entity::lock.tank300") is None
    assert "lock.tank300" not in hw._entity_claimed_entities
    assert "entity::lock.tank300" not in hw.registered_device_ids
    data = json.loads(Path(hw._entity_whitelist_file).read_text(encoding="utf-8"))
    assert data["entities"] == []


def test_whitelist_roundtrip(hw):
    """白名单文件加载/保存往返"""
    hw._entity_whitelist.update(["lock.a", "switch.b", "button.c"])
    hw._save_entity_whitelist()

    # 模拟进程重启：清空内存并重新加载
    hw._entity_whitelist.clear()
    hw._whitelist_loaded = False
    hw._load_entity_whitelist()

    assert hw._entity_whitelist == {"lock.a", "switch.b", "button.c"}


def test_load_idempotent(hw):
    Path(hw._entity_whitelist_file).write_text(
        json.dumps({"entities": ["lock.x"]}), encoding="utf-8")
    hw._load_entity_whitelist()
    hw._entity_whitelist.add("manual.added")
    hw._load_entity_whitelist()  # 第二次调用应为 no-op
    assert "manual.added" in hw._entity_whitelist
