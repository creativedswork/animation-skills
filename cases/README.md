# 制作案例

本目录现有 9 个任务定义。`sit-stand` 与 `low-seat-transfer` 已有制作记录和可预览动画，其余 7 个尚待制作；当前没有完整的接受评价。它们使用已存在的 Meshy 角色；场景道具由 Blender 基础几何制作。原始 GLB 中的动作禁止复用，以便比较动作制作能力。

| 能力 | 开发案例 | 公开迁移案例 |
| --- | --- | --- |
| 身体力学 | [行走转停](walk-turn-stop/case.json)、[坐下起立](sit-stand/case.json) | [低凳起身迈步](low-seat-transfer/case.json) |
| 物体交互 | [搬起重箱](lift-heavy-box/case.json)、[双手斧击](axe-strike/case.json) | [宽箱转身放低台](wide-crate-transfer/case.json) |
| 身体表演 | [警觉转身](alert-turn/case.json)、[疲惫行走](tired-walk/case.json) | [确认安全后放松](relief-transfer/case.json) |

初版只覆盖同一双足角色的动作、道具和情境变化。不同骨架、体型、四足、面部及多人交互尚未覆盖，不能从这些任务推断支持。

## 运行与预览

`case.json` 是给制作 Agent 的任务说明，包含输入、场景、动作时长、交付物和评价标准。当前没有执行任意 `case.json` 并自动完成动画的通用命令。

已有两个案例可直接运行 Blender 脚本重建：

| Case | 制作脚本 |
| --- | --- |
| `sit-stand` | `tools/production/sit_stand.py` |
| `low-seat-transfer` | `tools/production/low_seat.py` |

以新一轮坐下起立为例，在仓库根目录运行；`blender` 指向本机 Blender 5.1 可执行文件：

```bash
python3 tools/project.py new-run sit-stand trial-02
blender --background --factory-startup --disable-autoexec \
  --python tools/production/sit_stand.py -- trial-02
```

`trial-02` 是本轮记录 ID 和输出目录名，重跑时换成未使用的名字。脚本生成 `.artifacts/production/sit-stand/trial-02/editable.blend` 与 `animation.glb`，保留模型、材质、骨架和新制作的动作；视频录制与评价另行执行。

启动 `make viewer`，打开 `http://127.0.0.1:8765`，点击“载入 GLB”选择新生成的 `animation.glb` 即可播放。首次安装查看器依赖先运行 `npm ci`。已有登记的作品可直接在案例素材列表中选择。

临时载入不会修改运行记录。要让新作品长期出现在对应案例的素材列表中，在 `cases/sit-stand/runs/trial-02.json` 的 `initial.artifacts` 中登记 `role=export`、GLB 的仓库相对 `path` 和实际 `sha256`，再执行 `python3 tools/project.py check --artifacts`，刷新页面并选择该记录。用 `shasum -a 256 <文件路径>` 可取得文件指纹。完整记录还需工程、录像和实际评价；格式见 [工程约定](../docs/engineering.md)。

`tools/production/register.py` 仅登记首次两段坐站作品，不是新运行的通用登记命令。重建、录像与回读检查的细节见 [两段坐站动作](../docs/seated-motion.md)。

其余案例按下节准备输入和运行记录，再由 Agent 读取任务及对应 Skill，在 Blender 中制作并导出；创建记录本身不会生成动画。

## 开始一次制作

在仓库根目录执行：

```bash
python3 tools/project.py check --artifacts
python3 tools/project.py prepare walk-turn-stop .artifacts/work/walk-turn-stop
python3 tools/project.py new-run walk-turn-stop candidate-001
```

`prepare` 生成 `task.json`、`inputs.json` 和校验过的 `inputs/`。只把这个目录及指定 Skill 包交给制作 Agent。外部 harness 负责隔离访问，不能让制作 Agent 同时读取本仓库的其他作品和评价；`prepare` 自身不是沙箱。

`new-run` 记录当前任务、完整 Skill 集和输入的指纹，并创建 pending 记录。它不启动 Blender、不调用模型或 Meshy。运行前填写环境与预算，运行后记录实际消耗和帮助。不要在制作之后用新版本指纹替换运行时版本。

## 比较与完善

首次优先执行行走转停、重箱和警觉三个开发案例，每个能力一个实际作品。对同一任务比较不带 Skill 的基线与带 Skill 的候选，固定模型版本、harness、工具、预算、输入和评价尺度。用 `new-run walk-turn-stop baseline-001 --without-skills` 创建基线，其 `fingerprints.skills` 为空对象；候选记录完整安装集。

保留初稿、失败尝试和修正版。修改后的作品证明这次制作有所改善；用改进后的 Skill 从原始输入重新制作，才检验知识迁移。结果接近或随机波动明显时，重复成对运行并报告分布，不用单次分数宣布提升。

评价者先原速观看、不看版本标签，记录是否读懂意图，再逐项检查技术细节。正确性给通过与依据；品味按 case 的标准给 1–5 分。记录视频时间点、视图和可观察动作，少用“自然”“有力”等无定位形容词。

将确认有效的方法写入 `lessons/`，注明适用范围和局限，再修改相应 Skill。候选方法保持 `candidate`；有接受作品及更新后迁移证据再提升为 `promoted`。

公开迁移案例可用于回归，不能宣称它们是盲测。若要评价泛化能力，由独立评价者保管未公开的新任务。记录格式与正式发布条件见 [工程约定](../docs/engineering.md)。
