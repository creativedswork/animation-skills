# 七段新增动作

2026-09-28 在固定原始角色上制作了以下动画。每段都有独立 GLB 和可编辑 Blender 工程，查看器从运行记录选择作品。两段行走同时保留初稿与修正版，默认选择修正版。作品尚待独立品味评价，Skill 仍为 `draft`。

| Case | 动作 | 时长 | 制作脚本 |
| --- | --- | --- | --- |
| `walk-turn-stop` | 前进 2 m、右转、再前进 1 m 并停稳 | 6 s | `walk_turn.py` |
| `tired-walk` | 疲惫前行 2 m、喘息、重新抬头 | 7 s | `tired_walk.py` |
| `lift-heavy-box` | 搬起重箱、侧移、放上台面后松手 | 8 s | `heavy_box.py` |
| `axe-strike` | 蓄力、一次斧击、冲击停顿、收回 | 6 s | `axe.py` |
| `alert-turn` | 刺激后判断、换脚转向右后方 | 5 s | `alert.py` |
| `wide-crate-transfer` | 抱起宽箱、左转、放上低台 | 8 s | `wide_crate.py` |
| `relief-transfer` | 注视左前方、确认、呼气放松、注意力回前方 | 6 s | `relief.py` |

脚本位于 `tools/production/`。本地文件位于 `.artifacts/production/<case>/initial/`；`walk-turn-stop` 和 `tired-walk` 的当前版本位于 `corrected/`。大文件不进入 Git 或 Skill 安装包。

## 预览

运行 `make viewer`，打开 `http://127.0.0.1:8765`，选择左侧案例即可播放已登记作品。素材列表可切回初稿。新增“握持近景”和“接触近景”镜头；行走镜头覆盖完整路径，宽箱镜头兼顾转身后的动作。

也可点击“载入 GLB”，选择任意新导出的 `animation.glb`。临时载入仅影响浏览器，不修改运行记录。

## 制作与回读

本轮使用 Blender 5.1.1、Three.js 查看器和 Chrome 153。原始模型归一到 1.8 m，保留绑定、材质和 17 根骨骼；没有使用输入的 Idle、Walk 或 Chop 关键帧，也没有调用收费生成。

每段逐帧写入角色骨骼；双手交互以道具轨迹驱动掌心目标，用固定骨长求解手臂。角色与道具的活动 Action 合并为同一个 GLB 片段。导出动画从零时刻开始。

`reimport-check.json` 记录所有采样帧的骨盆、膝盖、脚踝及握持目标对照。新增作品及两份修正版的最大关节回读误差小于 0.000002 m，掌心目标误差小于 0.000001 m，道具位置误差为零。该检查证明导出一致性，不证明实际手套或鞋底网格完全无穿插。

`contact-summary.json` 记录部分任务的终点与接触位置：普通行走终点约为 `(1, 2)` m，疲惫行走终点约为 `(0, 2)` m；重箱和宽箱的最终箱底分别位于 0.75 m 与 0.45 m 台面；斧刃在 2.9 s 到达 `(0, 0.85, 0.55)` m，未继续向下穿过木墩。

## 视频与限制

各目录按任务保存 `main.mp4`，以及正面、侧面、握持或接触近景视频。最终视频由 `render_video.mjs` 逐帧输出：通过查看器公开时间轴采样 `frame / fps`，等待 Three.js 渲染，再按相同帧率合成视频。分辨率为 1920×1080，帧率为 30 fps，没有变速或插帧。各镜头的 `*-rendering.json` 保存方法、浏览器版本、实际帧数和媒体时长。

逐帧视频用于观看完整动作；查看器运行验证另存于 `.artifacts/production/catalog-check.json`，9 个案例均经过默认素材选择、片段时长和公开播放按钮检查。

早期实时录屏遇到卡顿和首帧缺失，不能用于原速评分，已作为诊断材料保留在 `*-realtime.mp4`、`*-first-take.mp4` 等文件中。查看器同步修复了大帧间隔被截断和播放起点沿用暂停前时间的问题；后台切换仍自动暂停。`recording.json` 是实时录制的历史记录，不是最终逐帧视频的元数据。

画面检查发现两段行走初稿骨盆偏低，已另存修正版：普通行走按双脚可达范围抬高经过姿势，疲惫行走减少持续下蹲。原始工程和录像继续保留。

角色没有手指、脚趾或眼球骨。手套局部穿插、精细包握、脚掌滚动与服装碰撞仍有限制。独立评价者还需按各 case 判断重量、节奏与表演意图；当前没有完整接受评价，也没有据此宣称 Skill 能力提升。

两个公开迁移任务先于其他新增任务制作，起点均为固定原始 GLB，未提供其他任务的成品关键帧。它们仍由同一 Agent、同一骨架和公开要求完成，不是盲测或与无 Skill 基线的受控对照。

## 重建命令

在仓库根目录执行；将 `blender` 替换为本机可执行文件，输出名称必须尚未使用：

```bash
blender --background --factory-startup --disable-autoexec \
  --python tools/production/axe.py -- trial-02

blender --background --factory-startup --disable-autoexec \
  --python tools/production/reimport.py \
  -- .artifacts/production/axe-strike/trial-02
```

视频工具需要本机已有的 Playwright、Chrome 和 FFmpeg。第一个参数为 Playwright 的 `index.mjs` 路径，后续参数是 case 和输出目录名：

```bash
node tools/production/render_video.mjs <playwright/index.mjs> axe-strike trial-02
```

脚本先生成 `main-offline.mp4` 等文件，以免覆盖已有录像；核对后将其登记为当前视频。`record_viewer.mjs` 仅保留用于实时录屏诊断。

`register_remaining.py` 只维护本轮 `20260928-first-motion` 的七份记录，不是任意运行的通用登记工具。新运行按[工程约定](engineering.md)另建记录，填写实际指纹、产物和评价。
