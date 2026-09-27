# 两段坐站动作

查看器已有两段从固定原始角色重新制作的动画。使用 Blender 5.1.1 制作、Three.js 0.180.0 播放，未调用付费生成服务。

| 案例 | 默认作品 | 动作与证据目录 |
| --- | --- | --- |
| 坐下与起立 | 初稿 `SitStand`，7 秒 | 站立 → 坐下 → 稳定坐住 1.2 秒 → 无手支撑起立；`.artifacts/production/sit-stand/initial/` |
| 低凳起身并迈步 | 修正版 `LowSeatRiseStep`，6 秒 | 低坐姿 → 前倾起立 → 右脚承重、左脚前迈 0.42 m → 停稳；`.artifacts/production/low-seat-transfer/corrected/` |

刷新查看器，选择案例后点击播放。素材列表保留低凳初稿，供比较坐姿悬空的修正；初稿位于 `.artifacts/production/low-seat-transfer/initial/`。这些动作是单次任务，查看末尾停稳时取消“循环”。

每个作品目录包含可编辑的 `editable.blend`、含木凳的 `animation.glb`，以及主视角 `main.mp4` 和侧视角 `side.mp4`。视频采集自实际 Three.js 画布，1920 × 1080，播放速度为 1×；浏览器录制可能丢帧，低凳修正版录像保留操作前后的短暂停留。

## 已验证的范围

- 浏览器实际加载两段动画，播放时角色姿势发生变化；`viewer-check.json` 记录片段名称、时长、加载来源及浏览器错误。
- 主视角和侧面截图位于 `views/`，覆盖坐姿、前倾、站立和迈步。低凳初稿坐姿悬空，修正版初始骨盆降低 0.08 m 后，侧面可见衣摆与座面接触。
- `reimport-check.json` 对低凳修正版的 181 帧、普通凳初稿的 211 帧逐帧回读。均保留 17 根骨骼，与制作工程的关节位置最大误差低于 0.001 mm。
- 支撑脚踝世界坐标保持稳定。该数值不等于鞋底网格接触误差；尚未建立衣物碰撞和脚趾滚动。

运行记录保持 `recording / pending`。本轮证明对应动作已制作并接入；尚无独立动画师评分，不据此标记 Skill 已验证或推广经验。其他 7 项案例仍待制作。

## 重建与检查

在仓库根目录运行。将 `blender` 换成可用的 Blender 5.1 可执行文件；新版本名必须对应未使用的目录，脚本拒绝覆盖已保存工程。

```bash
blender --background --factory-startup --disable-autoexec \
  --python tools/production/sit_stand.py -- trial-02
blender --background --factory-startup --disable-autoexec \
  --python tools/production/low_seat.py -- trial-02
blender --background --factory-startup --disable-autoexec \
  --python tools/production/reimport.py -- .artifacts/production/sit-stand/trial-02
```

脚本保留原始绑定，清除源动作，用独立节拍、骨盆曲线和定长两段腿部求解生成可编辑关键帧。制作脚本属于 case 工程工具，不进入 Skill 发布包。低凳任务在其他作品出现前从原始输入制作，普通凳随后制作；不能将二者视为独立模型间的对照实验。

启动 `make viewer` 后，浏览器检查和录像脚本接受已安装的 Playwright 模块入口：

```bash
node tools/production/inspect_viewer.mjs /path/to/playwright/index.mjs sit-stand initial
node tools/production/record_viewer.mjs /path/to/playwright/index.mjs sit-stand initial
```

需要本机 Chrome 与 FFmpeg；录像脚本仅为取证调整画布尺寸，不改变角色轨迹或播放时钟。`tools/production/register.py` 专门登记本轮的初稿与修正版，重新计算文件指纹，不创建新运行或给作品评分。新一轮制作应先使用 `project.py new-run` 创建独立记录。
