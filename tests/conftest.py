"""测试夹具：stub 掉 homeassistant/psutil/aiofiles 依赖，提供假 hass 对象。

无需真实 Home Assistant 环境即可测试桥接核心逻辑。
"""
import sys
import types
import asyncio
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 模块 stub 基础设施
# ---------------------------------------------------------------------------

class _Any:
    """通用占位类型"""

    def __init__(self, *args, **kwargs):
        pass


class _AsyncFile:
    """aiofiles.open 的最小可用替身（支持读）"""

    def __init__(self, path, mode="r", encoding=None, **kwargs):
        self._path = str(path)
        self._mode = mode

    async def read(self):
        return Path(self._path).read_text(encoding="utf-8")

    async def write(self, data):
        Path(self._path).write_text(data, encoding="utf-8")
        return len(data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _aio_open(path, mode="r", encoding=None, **kwargs):
    return _AsyncFile(path, mode, encoding)


def _module(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


class _EmptyRegistry:
    """dr/er/ar.async_get 的空注册表替身"""

    def __init__(self):
        self.entities = types.SimpleNamespace(values=lambda: [], get=lambda eid: None)
        self.devices = types.SimpleNamespace(
            values=lambda: [], keys=lambda: [], get=lambda did: None)

    def async_get(self, hass):
        return self

    def async_get_device(self, identifiers=None, **kwargs):
        return None

    def async_entries_for_device(self, reg, device_id):
        return []

    def async_get_or_create(self, **kwargs):
        return None

    def async_remove_device(self, device_id):
        pass

    def async_update_device(self, device_id, **kwargs):
        pass

    def async_get_area(self, area_id):
        return None


def _setup_stubs():
    ha = _module("homeassistant")
    core = _module("homeassistant.core", HomeAssistant=_Any, callback=lambda f: f)
    ha_const = _module("homeassistant.const",
                       EVENT_HOMEASSISTANT_STARTED="homeassistant_started",
                       EVENT_STATE_CHANGED="state_changed")
    config_entries = _module("homeassistant.config_entries", ConfigEntry=_Any)
    helpers = _module("homeassistant.helpers")
    dr = _module("homeassistant.helpers.device_registry",
                 EVENT_DEVICE_REGISTRY_UPDATED="device_registry_updated")
    er = _module("homeassistant.helpers.entity_registry")
    ar = _module("homeassistant.helpers.area_registry")

    empty = _EmptyRegistry()
    dr.async_get = lambda hass: empty
    er.async_get = lambda hass: empty
    er.async_entries_for_device = lambda reg, device_id: []
    ar.async_get = lambda hass: empty

    # 防御性父属性链
    ha.core = core
    ha.const = ha_const
    ha.config_entries = config_entries
    ha.helpers = helpers
    helpers.device_registry = dr
    helpers.entity_registry = er
    helpers.area_registry = ar

    _module("psutil", net_if_addrs=lambda: {})
    _module("aiofiles", open=_aio_open)


_setup_stubs()


# ---------------------------------------------------------------------------
# 假 hass 对象
# ---------------------------------------------------------------------------

class FakeLoop:
    """记录调度而非真正执行"""

    def __init__(self):
        self.scheduled = []   # (delay, callback, args)
        self.immediate = []   # (callback, args)

    def call_later(self, delay, callback, *args):
        self.scheduled.append((delay, callback, args))
        return None

    def call_soon_threadsafe(self, callback, *args):
        self.immediate.append((callback, args))
        return None

    def run_in_executor(self, executor, fn, *args):
        # 同步执行，方便测试断言文件写入
        fn(*args)
        return None


class FakeState:
    def __init__(self, entity_id, state, attributes=None, name=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self._name = name

    @property
    def name(self):
        return self._name or self.entity_id


class FakeStates:
    def __init__(self):
        self._states = {}

    def add(self, state_obj):
        self._states[state_obj.entity_id] = state_obj

    def get(self, entity_id):
        return self._states.get(entity_id)

    def async_all(self, domains=None):
        result = []
        for state_obj in self._states.values():
            if domains is None or state_obj.entity_id.split(".")[0] in domains:
                result.append(state_obj)
        return result


class FakeEntityEntry:
    def __init__(self, entity_id, domain, disabled_by=None, platform="test",
                 device_class=None, original_name=None):
        self.entity_id = entity_id
        self.domain = domain
        self.disabled_by = disabled_by
        self.platform = platform
        self.device_class = device_class
        self.original_name = original_name


class FakeEntityRegistry:
    def __init__(self):
        self.entities = {}

    def add(self, entry):
        self.entities[entry.entity_id] = entry


class FakeConfig:
    def __init__(self, base="/tmp/fake-hass"):
        self._base = base
        self.language = "zh-Hans"

    def path(self, *parts):
        return str(Path(self._base).joinpath(*parts))


class FakeHass:
    def __init__(self, base=None):
        self.states = FakeStates()
        self.loop = FakeLoop()
        self.config = FakeConfig(base)
        self.data = {}


# ---------------------------------------------------------------------------
# 共享夹具
# ---------------------------------------------------------------------------

@pytest.fixture
def router():
    """加载真实产品注册表 JSON 的 ServiceRouter"""
    from custom_components.hwhomebridge.service_router import ServiceRouter

    instance = ServiceRouter()
    config_path = REPO_ROOT / "custom_components/hwhomebridge/config/product_registry.json"
    ok = asyncio.run(instance.load_product_registry(str(config_path)))
    assert ok, "product registry failed to load"
    return instance


@pytest.fixture
def hw(tmp_path):
    """重置 hwbridge 模块全局状态的干净实例"""
    from custom_components.hwhomebridge import hwbridge

    hwbridge.ghass = None
    hwbridge.service_router = None
    hwbridge.registered_device_ids.clear()
    hwbridge.saved_device_ids.clear()
    hwbridge._excluded_device_sns.clear()
    hwbridge._entity_claimed_entities.clear()
    hwbridge._disabled_device_sns.clear()
    hwbridge._entity_whitelist.clear()
    hwbridge._whitelist_loaded = False
    hwbridge._entity_whitelist_file = str(tmp_path / "entity_whitelist.json")
    hwbridge.saved_device_file = str(tmp_path / "new_device.txt")
    hwbridge.excluded_devices_file = str(tmp_path / "excluded_devices.txt")
    yield hwbridge

    hwbridge.ghass = None
    hwbridge.service_router = None
