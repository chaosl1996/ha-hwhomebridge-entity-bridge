"""Constants for hwhomebridge integration."""

DOMAIN = "hwhomebridge"

# 来自这些集成（platform）的实体不做映射，避免循环接入。
# 例如社区插件 ha-huawei-smarthome（domain: huawei_smarthome）将华为设备接入 HA，
# 若再次桥接回华为会导致设备循环。
SKIP_PLATFORMS = {"huawei_smarthome"}

# 实体级虚拟设备的伪 device_id 前缀：entity::<entity_id>
# 用于白名单/entity_keyword 命中的单实体注册（一个实体一个华为设备），
# SN 由该伪 device_id 哈希生成，与设备级注册互不冲突。
ENTITY_DEVICE_PREFIX = "entity::"

# 实体白名单持久化文件（位于 .storage/hwhomebridge/config/ 下）。
# 记录通过配置界面"添加实体"勾选的实体，重启后自动重新注册。
ENTITY_WHITELIST_FILE = "entity_whitelist.json"

# 支持实体级注册（白名单直连）的 domain。
# 对应华为品类：light → 002（灯，全功能），其余 → 008（断路器 on/off 包装）。
BRIDGEABLE_DOMAINS = (
    "switch",
    "light",
    "input_boolean",
    "script",
    "scene",
    "fan",
    "lock",
    "button",
    "siren",
    "valve",
    "humidifier",
)

# lock 实体中视为"开"的状态（华为 008 开关语义：on=已开锁）
LOCK_ON_STATES = {"unlocked", "unlocking", "jammed"}


def ha_state_to_switch_value(entity_domain: str, state_value: str) -> int:
    """将 HA 实体状态归一化为华为开关值（1=on，0=off）

    - lock: unlocked/unlocking/jammed → 1，locked/locking → 0
    - button/scene: 无真实开关状态，恒为 0
    - 其余 domain: on → 1，其余 → 0

    Args:
        entity_domain: 实体的 HA domain（entity_id 的前缀）
        state_value: HA state 字符串

    Returns:
        1 表示开，0 表示关
    """
    if entity_domain == "lock":
        return 1 if state_value in LOCK_ON_STATES else 0
    if entity_domain in ("button", "scene"):
        return 0
    return 1 if state_value == "on" else 0
