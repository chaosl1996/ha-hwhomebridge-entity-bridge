"""ServiceRouter 实体级注册与直连映射测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs  # noqa: F401
_setup_stubs()

from custom_components.hwhomebridge.product_registry import AdapterDef
from custom_components.hwhomebridge.virtual_device import SNManager


def test_register_direct_entity_lock(router):
    vd = router.register_direct_entity(
        "entity::lock.tank300", "坦克300 车门锁",
        [{"entity_id": "lock.tank300", "domain": "lock", "name": "车门锁"}])

    assert vd is not None
    assert vd.product.pid == "008"
    assert vd.ha_device_id == "entity::lock.tank300"
    # 所有服务直接绑定到 lock 实体（不做 domain 匹配）
    assert vd.get_entity_for_service("switch") == "lock.tank300"
    assert vd.service_entries["switch"].domain == "lock"
    # SN 确定性
    assert vd.sn == SNManager.generate_sn("entity::lock.tank300")


def test_register_direct_entity_light(router):
    vd = router.register_direct_entity(
        "entity::light.bedroom", "卧室灯",
        [{"entity_id": "light.bedroom", "domain": "light", "name": "卧室灯"}])

    assert vd is not None
    assert vd.product.pid == "002"
    assert vd.get_entity_for_service("switch") == "light.bedroom"
    # 002 的亮度/色温服务也应直接绑定到同一实体
    for svc_id in ("brightness", "cct"):
        if svc_id in vd.service_entries:
            assert vd.get_entity_for_service(svc_id) == "light.bedroom"


def test_entity_level_bypasses_include_exclude(router):
    """entity_level 注册必须跳过默认适配器的 include/exclude 关键词过滤。

    default_008 的 switch 服务 include_keywords 含 开关/power 等、
    exclude_keywords 含 lock/timer —— button/lock 实体按 domain 匹配
    本来必被过滤掉，实体级直连后必须能绑定。
    """
    # 注入一个 entity_keyword 适配器（模拟高级用户的自定义适配器）
    adapter = AdapterDef(pid="008", match_rules=[],
                         services={"switch": {"domain": "switch",
                                              "action": "turn_on_off",
                                              "value_attr": "state"}})
    from custom_components.hwhomebridge.product_registry import EntityKeywordMatch
    adapter.match_rules.append(EntityKeywordMatch(keywords=["doorbell"]))
    router.registry._adapters.append(adapter)

    vd = router.register_device(
        device_id="entity::button.doorbell",
        device_name="门铃",
        entity_list=[{"entity_id": "button.doorbell", "domain": "button",
                      "name": "门铃"}],
        entity_level=True)

    assert vd is not None
    assert vd.product.pid == "008"
    assert vd.get_entity_for_service("switch") == "button.doorbell"


def test_entity_level_without_adapter_returns_none(router):
    vd = router.register_device(
        device_id="entity::lock.nomatch",
        device_name="未声明锁",
        entity_list=[{"entity_id": "lock.nomatch", "domain": "lock",
                      "name": "锁"}],
        entity_level=True)
    assert vd is None


def test_register_direct_entity_keeps_entity_name(router):
    """白名单直通注册必须把实体名保存到 vd.name。

    OnGetRoomInfoCB 上云取名时，实体级设备的 ha_device_id 是伪 ID
    （device_registry 中无对应条目），必须靠 vd.name 兜底，
    否则华为 App 中所有白名单设备显示同名（如“智控断路器”）。
    """
    vd = router.register_direct_entity(
        "entity::switch.pdu_port3", "PDU 3口",
        [{"entity_id": "switch.pdu_port3", "domain": "switch",
          "name": "PDU 3口"}])

    assert vd is not None
    assert vd.name == "PDU 3口"
