# 制作案例

本目录现有 9 个任务定义，尚无制作运行或接受评价。它们使用已存在的 Meshy 角色；场景道具由 Blender 基础几何制作。原始 GLB 中的动作禁止复用，以便比较动作制作能力。

| 能力 | 开发案例 | 公开迁移案例 |
| --- | --- | --- |
| 身体力学 | [行走转停](walk-turn-stop/case.json)、[坐下起立](sit-stand/case.json) | [低凳起身迈步](low-seat-transfer/case.json) |
| 物体交互 | [搬起重箱](lift-heavy-box/case.json)、[双手斧击](axe-strike/case.json) | [宽箱转身放低台](wide-crate-transfer/case.json) |
| 身体表演 | [警觉转身](alert-turn/case.json)、[疲惫行走](tired-walk/case.json) | [确认安全后放松](relief-transfer/case.json) |

初版只覆盖同一双足角色的动作、道具和情境变化。不同骨架、体型、四足、面部及多人交互尚未覆盖，不能从这些任务推断支持。

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
