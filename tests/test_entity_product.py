"""build_entity_product 白名单直通产品构建测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs  # noqa: F401
_setup_stubs()

from custom_components.hwhomebridge.product_registry import ProductRegistry


def _make_registry():
    reg = ProductRegistry()
    reg._products["008"] = _fake_product_008()
    reg._defaults["008"] = _fake_default_008()
    return reg


def _fake_product_008():
    from custom_components.hwhomebridge.product_registry import (
        ProductDef, ServiceDef, HAMapping)

    product = ProductDef(pid="008", name="断路器",
                         auto_match={"required_domains": ["switch"]})
    product.services["switch"] = ServiceDef(
        service_id="switch", service_type="switch", char_name="on",
        ha_mapping=HAMapping(domain="switch", action="turn_on_off",
                             value_attr="state",
                             include_keywords=["开关", "power"],
                             exclude_keywords=["lock", "timer"]))
    product.services["electric"] = ServiceDef(
        service_id="electric", service_type="electric", char_name="electric",
        ha_mapping=HAMapping(domain="sensor", action="read_only",
                             value_attr="state"))
    return product


def _fake_default_008():
    from custom_components.hwhomebridge.product_registry import AdapterDef
    return AdapterDef(pid="008", services={
        "switch": {"domain": "switch", "action": "turn_on_off",
                   "value_attr": "state",
                   "include_keywords": ["开关", "power"],
                   "exclude_keywords": ["lock", "timer"]},
        "electric": {"domain": "sensor", "action": "read_only",
                     "value_attr": "state"},
    })


def test_008_entity_product_strips_readonly_and_filters():
    reg = _make_registry()
    product = reg.build_entity_product("008", "坦克300 车门锁")

    assert product is not None
    assert product.name == "坦克300 车门锁"
    assert product.auto_match is None
    # read_only 服务被剔除，仅剩 switch
    assert set(product.services.keys()) == {"switch"}
    mapping = product.services["switch"].ha_mapping
    assert mapping.include_keywords is None
    assert mapping.exclude_keywords is None
    assert mapping.on_command is None
    assert mapping.action == "turn_on_off"


def test_base_product_not_mutated():
    reg = _make_registry()
    reg.build_entity_product("008", "x")
    # 框架层原产品不受影响
    assert set(reg._products["008"].services.keys()) == {"switch", "electric"}
    assert reg._products["008"].services["switch"].ha_mapping.include_keywords == ["开关", "power"]
    assert reg._products["008"].auto_match == {"required_domains": ["switch"]}


def test_unknown_pid_returns_none():
    reg = _make_registry()
    assert reg.build_entity_product("999") is None
