"""const.ha_state_to_switch_value 状态归一化测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import _setup_stubs  # noqa: F401  确保 stub 先于被测模块安装
_setup_stubs()

from custom_components.hwhomebridge.const import ha_state_to_switch_value


def test_lock_states():
    assert ha_state_to_switch_value("lock", "unlocked") == 1
    assert ha_state_to_switch_value("lock", "unlocking") == 1
    assert ha_state_to_switch_value("lock", "jammed") == 1
    assert ha_state_to_switch_value("lock", "locked") == 0
    assert ha_state_to_switch_value("lock", "locking") == 0


def test_momentary_domains():
    assert ha_state_to_switch_value("button", "2026-10-11T00:00:00+00:00") == 0
    assert ha_state_to_switch_value("button", "unknown") == 0
    assert ha_state_to_switch_value("scene", "unknown") == 0


def test_normal_domains():
    assert ha_state_to_switch_value("switch", "on") == 1
    assert ha_state_to_switch_value("switch", "off") == 0
    assert ha_state_to_switch_value("input_boolean", "on") == 1
    assert ha_state_to_switch_value("script", "on") == 1
    assert ha_state_to_switch_value("script", "off") == 0
    assert ha_state_to_switch_value("switch", "unavailable") == 0
