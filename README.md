# Konke Smart for Home Assistant

本项目是一个基于最新版本 Home Assistant 而开发的关于控客智能的集成。目的是在于把控客智能 App 中已经保存的设备能够通过 Home Assistant 进行桥接，与其他品牌的设备进行联动，从而完成部分自动化。

## 安装

1. 将本目录里的 `custom_components/konke` 复制到 Home Assistant 的 `/config/custom_components/konke`。
2. 重启 Home Assistant。
3. 进入 `设置 -> 设备与服务 -> 添加集成`，搜索 `控客智能` 或 `Konke Smart`。
4. 选择登录方式：
   - `Access Token`: 填控客 `accessToken`，最快。
   - `手机号和密码`: 填控客账号手机号和密码，由集成登录并保存 token。

## 已确认接口

- API: `https://kapp.ikonke.com/api/`
- account: `https://kapp.ikonke.com/account/`
- appKey: `1592290148`
- 场景执行: `POST /api/scene/action`

控客 App 中已有场景会作为 HA 场景同步：

- `<scene_id>` - `<scene_name>`

安装后它会作为 HA 的 `scene` 实体出现，可以直接在自动化里调用 `scene.turn_on`。

## 实体

### 场景

控客场景会同步为 HA `scene` 实体。

### 空调

控客空调会同步为 HA `climate` 实体。当前已实现：

- 在线/离线状态
- 当前开关状态
- 当前温度
- 目标温度
- 当前模式展示
- `climate.turn_off`
- 设备注册表信息：设备名、型号、建议区域、父子设备关系

当前暂未实现：

- `climate.turn_on`
- 设置温度
- 设置模式
- 设置风速

这些能力需要继续抓包确认对应控客命令 payload 后再开启。未确认前不会在 HA 中冒充支持，避免自动化误操作。

## 选项

集成选项中可以调整：

- 刷新间隔。
- 是否创建场景实体。
- 是否创建离线设备实体。
- 是否启用调试用 `konke.raw_command` 服务。
- 是否允许后台用保存的手机号/密码重新登录。

`konke.raw_command` 默认关闭，只用于抓包验证后的开发调试，不建议在日常自动化中使用。

后台密码重新登录默认关闭。这样即使控客云端采用“新登录使旧登录态失效”的策略，HA 也不会在 token 失效后自动用密码登录，从而把手机 App 或模拟器 App 顶下线。关闭时，token 失效后 HA 会进入重新认证流程；确实需要无人值守自动重登时，再在选项里手动开启。

## 服务

也可以直接调用服务：

```yaml
service: konke.execute_scene
data:
  scene_id: <scene_id>
```

手动刷新控客云端数据：

```yaml
service: konke.refresh
```

如果 HA 里配置了多个控客账号，可以加 `entry_id` 指定配置项。

### 空调设备

当前版本还提供空调设备筛选和关机服务，用于按房间排除或包含设备的自动化。

先试运行，确认会匹配哪些设备：

```yaml
service: konke.turn_off_air_conditioners
data:
  exclude_room_names:
    - <排除房间名>
  only_on: true
  dry_run: true
```

确认列表正确后再实际执行：

```yaml
service: konke.turn_off_air_conditioners
data:
  exclude_room_names:
    - <排除房间名>
  only_on: true
```

也可以只列出设备，不发送控制命令：

```yaml
service: konke.list_air_conditioners
data:
  exclude_room_names:
    - <排除房间名>
```

## 注意

- 这是云端接口集成，不是局域网本地协议。
- 控客 token 和密码会保存在 HA 配置存储中，请确保 HA 主机可信。
- 为避免和控客手机 App/模拟器抢登录态，集成默认不会在后台用保存的手机号/密码自动重新登录。
- 空调关机使用 `/api/device/action/control` 和 `name: TurnOff`。如果控客云返回 payload 不兼容，需要用抓包结果调整 `KonkeApiClient.turn_off_air_conditioner()`。
- 新风、地暖、窗帘等独立实体还没有启用；当前已建立设备能力模型，后续可继续补 `fan`、`climate`、`cover` 等平台。
