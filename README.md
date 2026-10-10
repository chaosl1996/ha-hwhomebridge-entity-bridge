# HuaweiHome Bridge (Entity Bridge)

Home Assistant → 华为智慧生活（HiLink）桥接集成，融合 **HomeKit Bridge 的自由勾选体验** 与 **hwhomebridge 的华为 HiLink 接口**。

在原版 [ha_hwhomebridge](https://github.com/Wangxiaokang666-666/ha_hwhomebridge)（Apache-2.0）基础上增加"**添加实体**"功能：像 HomeKit Bridge 一样，在配置界面勾选**任意实体**即可接入华为智慧生活——无需再为单实体（锁、按钮、脚本、场景、Node-RED 实体等）手工创建 HA 设备、写 template 包装或适配器 JSON。

## 特性

- **添加实体（新）**：集成 → 配置 → 添加实体 → 勾选任意实体，立即接入华为智慧生活，取消勾选立即移除，重启后保持。
- **锁 / 瞬时按钮 / 脚本 / 场景免包装直连**（新）：
  - `lock`：华为开关 on → `lock.unlock`，off → `lock.lock`；状态 `unlocked→on`、`locked→off` 自动归一化
  - `button`：华为开关拨动即触发 `button.press`（瞬时态自动回弹）
  - `script` / `scene`：on → `turn_on`；off 时 script 调 `turn_off`、scene 忽略
  - `input_boolean` / `switch` / `fan` / `siren` / `valve` / `humidifier`：标准 turn_on/turn_off
  - `light`：002 灯品类全功能（开关 / 亮度 / 色温 / 颜色）
- **原有设备级自动发现完整保留**：有设备归属的实体仍按 HA 设备聚合接入，行为与原版一致。
- **原版 `entity_keyword` 适配器能力保留**（高级用法，白名单已覆盖绝大多数场景）。

## 安装

### 前置要求

> 如果你正在使用 HACS 安装的原版 hwhomebridge，请先在 HACS 中**删除原版仓库**（集成数据、华为 App 绑定关系与 SN 均保存在 `.storage/hwhomebridge/`，删除 HACS 仓库不会清掉它们），否则 HACS 可能在更新时把文件覆盖回原版。

### 方式一：HACS（推荐）

1. HACS → 右上角菜单 → 自定义存储库
2. 仓库地址：`https://github.com/chaosl1996/ha-hwhomebridge-entity-bridge`，类别选 **集成**
3. 安装 **HuaweiHome Bridge (Entity Bridge)**
4. 重启 Home Assistant

### 方式二：手动

1. 下载最新 release 中的 `hwhomebridge-entity-bridge.zip` 并解压
2. 将 `custom_components/hwhomebridge/` 覆盖复制到 HA 的 `config/custom_components/hwhomebridge/`
3. 重启 Home Assistant

## 使用

1. 已配置过原版的直接沿用原配置条目（domain 未变，绑定关系无缝继承）；首次使用则 添加集成 → 搜索 **HuaweiHome Bridge** → 提交
2. 集成页面 → **配置** → 选择 **添加实体**
3. 勾选要接入的实体（锁、按钮、脚本、场景、任意开关……）→ 提交，立即生效
4. 华为智慧生活 App 中即可看到对应设备（锁/按钮等显示为开关面板）

## 支持的实体类型

| HA domain | 华为品类 | 能力 |
|---|---|---|
| light | 002 灯 | 开关 / 亮度 / 色温 / 颜色 |
| switch / input_boolean / fan / siren / valve / humidifier | 008 断路器 | 开关 |
| **lock** | 008 断路器 | on=开锁 / off=上锁，状态双向归一化 |
| **button** | 008 断路器 | 拨动即触发 press，瞬时回弹 |
| **script / scene** | 008 断路器 | on 触发运行 |
| climate / cover / media_player / camera / sensor | — | 暂不支持（设备级自动发现仍可覆盖部分场景） |

## 与原版的技术差异

- `config_flow.py`：新增"添加实体"多选步骤，差集即时注册/注销
- `hwbridge.py`：白名单持久化（`.storage/hwhomebridge/config/entity_whitelist.json`）+ 实体级注册直通 + 锁状态归一化
- `service_router.py`：`register_direct_entity()`（light→002，其余→008）+ 实体级服务直连映射（跳过 domain/include/exclude 过滤）+ 按钮瞬时状态缓存
- `service_action.py`：按实体 domain 分发控制命令（lock/button/script/scene）
- `const.py`：`ha_state_to_switch_value()` 状态归一化、`BRIDGEABLE_DOMAINS` 白名单域

## 致谢

基于 [@Wangxiaokang666-666](https://github.com/Wangxiaokang666-666) 的 [ha_hwhomebridge](https://github.com/Wangxiaokang666-666/ha_hwhomebridge)（Apache-2.0）改造。

## License

Apache-2.0
