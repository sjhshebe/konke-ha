# Konke Smart for Home Assistant

本项目是一个基于最新版本 Home Assistant 而开发的关于控客智能的集成。目的是在于把控客智能 App 中已经保存的设备能够通过 Home Assistant 进行桥接，与其他品牌的设备进行联动，从而完成部分自动化。

## 安装

### 方式一：一键安装

在 Home Assistant 的 Terminal / SSH 中运行：

```bash
curl --retry 3 --retry-all-errors --connect-timeout 15 --max-time 120 -fsSL --http1.1 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/install.sh -o /tmp/konke-install.sh && sh /tmp/konke-install.sh
```

脚本会下载最新 GitHub Release 中的 `konke.zip`，安装到 Home Assistant
的 `custom_components/konke`，并在安装前备份旧版本。安装完成后会自动
重启 Home Assistant Core。

安装指定版本时设置 `KONKE_VERSION`：

```bash
curl --retry 3 --retry-all-errors --connect-timeout 15 --max-time 120 -fsSL --http1.1 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/install.sh -o /tmp/konke-install.sh && KONKE_VERSION=v0.6.0 sh /tmp/konke-install.sh
```

如果你的环境没有 `curl`，也可以使用：

```bash
wget -q -T 30 -t 3 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/install.sh -O /tmp/konke-install.sh && sh /tmp/konke-install.sh
```

### 方式二：手动安装

1. 从 GitHub Release 下载 `konke.zip`。
2. 解压后将 `custom_components/konke` 复制到 Home Assistant 的 `/config/custom_components/konke`。
3. 重启 Home Assistant。
4. 进入 `设置 -> 设备与服务 -> 添加集成`，搜索 `控客智能` 或 `Konke Smart`。
5. 选择 `手机号和密码` 登录，填写控客账号手机号和密码；集成会自动登录控客接口，并保存后续请求需要的 token。

## 更新

### 方式一：一键更新

以后更新到最新稳定版本时，在 Home Assistant 的 Terminal / SSH 中运行：

```bash
curl --retry 3 --retry-all-errors --connect-timeout 15 --max-time 120 -fsSL --http1.1 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/update.sh -o /tmp/konke-update.sh && sh /tmp/konke-update.sh
```

更新到指定版本时设置 `KONKE_VERSION`：

```bash
curl --retry 3 --retry-all-errors --connect-timeout 15 --max-time 120 -fsSL --http1.1 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/update.sh -o /tmp/konke-update.sh && KONKE_VERSION=v0.6.0 sh /tmp/konke-update.sh
```

如果你的环境没有 `curl`，也可以使用：

```bash
wget -q -T 30 -t 3 https://raw.githubusercontent.com/sjhshebe/konke-homeassistant/main/update.sh -O /tmp/konke-update.sh && sh /tmp/konke-update.sh
```

更新脚本会复用安装脚本的逻辑，自动备份旧版本、覆盖安装最新 Release，并
重启 Home Assistant Core。

### 方式二：手动更新

1. 从 GitHub Release 下载目标版本的 `konke.zip`。
2. 用新的 `custom_components/konke` 覆盖 Home Assistant 的 `/config/custom_components/konke`。
3. 重启 Home Assistant。

## Release 与 CI

- Release 版本号使用 `vX.Y.Z`，并且必须和 `custom_components/konke/manifest.json` 中的 `version` 一致。
- 每个 Release 会上传 `konke.zip`，包内只包含 `custom_components/konke/`。
- 一键安装和一键更新默认使用最新稳定 Release；如果 Release 不存在或缺少 `konke.zip`，脚本会失败并提示原因。
- 回滚到旧版本时，运行一键安装或一键更新命令并设置 `KONKE_VERSION`，例如 `KONKE_VERSION=v0.6.0`。
- GitHub Actions 会在 `main`、`dev` 的推送和 PR 上自动运行单元测试、编译检查和质量门禁；推送版本 tag 或手动触发 Release workflow 时会自动打包并发布 Release。

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

控客普通场景会同步为 HA `scene` 实体。控客 App 内部生成的多控分组
场景，例如 `空调多控`、`新风多控`，不会从云端场景同步请求中读取，也不
会创建为 HA 实体；这些分组更像控客内部设备关系说明，日常自动化应直接
使用对应的 `climate`、`cover` 等标准实体。

### 空调

控客空调会同步为 HA `climate` 实体。当前已实现：

- 在线/离线状态
- 当前开关状态
- 当前温度
- 目标温度
- 当前模式展示
- 当前风速展示
- `climate.turn_on`
- `climate.turn_off`
- 设置目标温度
- 设置模式：制冷、制热、送风、除湿
- 设置风速：自动、低、中、高
- 设备注册表信息：设备名、型号、建议区域、父子设备关系

### 地暖

控客地暖会同步为 HA `climate` 实体。当前已实现：

- 在线/离线状态
- 当前开关状态
- 当前温度
- 目标温度
- `climate.turn_on`
- `climate.turn_off`
- 设置目标温度
- 设置模式：自动、制热

### 窗帘

控客窗帘电机会同步为 HA `cover` 实体。当前已实现：

- 在线/离线状态
- 当前位置展示
- `cover.open_cover`
- `cover.close_cover`
- `cover.stop_cover`

### 新风

新风设备目前只完成了设备识别和只读状态分析，尚未暴露为可控制 HA 实体。原因是抓包只确认了一次 `TurnOn`，还没有确认 `TurnOff`、调风速和调模式的完整控制与恢复路径。

## 选项

集成选项中可以调整：

- 刷新间隔。
- 是否创建场景实体。
- 是否创建离线设备实体。
- 是否启用调试用 `konke.raw_command` 服务。
- 是否允许后台用保存的手机号/密码重新登录。

`konke.raw_command` 默认关闭，只用于抓包验证后的开发调试，不建议在日常自动化中使用。

使用手机号和密码登录时，后台密码重新登录默认开启。这样控客 access token 或 refresh token 失效后，HA 可以自动重新登录并恢复实体，不需要手工重新认证。如果你正在用手机 App 或模拟器抓包，担心 HA 自动登录把 App 挤下线，可以在集成选项里关闭这一项。

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
- 手机号和密码登录模式会默认允许后台自动重新登录；抓包调试时如需避免和控客手机 App/模拟器抢登录态，可以在集成选项中关闭。
- 已抓包确认的能力优先暴露为标准 HA 实体。日常自动化建议直接调用 `climate`、`cover`、`scene` 等标准服务。
- GitHub 仓库只包含源码和脱敏测试数据，不包含你的真实 HA 运行时设备清单。HA 的“下载诊断”会从本机实例生成数据，可能包含房间名、设备名、设备 ID 等家庭结构信息；只有你手动导出并发送给别人时才会泄露这些信息。
