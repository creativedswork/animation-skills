# 工程约定

本文件定义 Skill、case、经验记录和发布包之间的关系。实际执行调度由外部 harness 提供。

## 源码与发布单元

`.trae/skills/<name>/` 是 Skill 的唯一源码位置。每个 Skill 包含 `SKILL.md`，按需添加 `references/`、`scripts/` 和 `assets/`。这些目录之外的内容不进入安装包。

`catalog.json` 保存工程版本及 Skill 成熟度：

```json
{
  "version": "0.1.0-dev.1",
  "skills": [
    {"name": "character-body-mechanics", "maturity": "draft"},
    {"name": "character-prop-interaction", "maturity": "draft"},
    {"name": "character-acting", "maturity": "draft"}
  ]
}
```

`draft` 表示尚未完成制作评测；`validated` 表示已有对应作品和迁移证据。工具只检查证据记录完整性，不代替评价者判断画面。正式包要求全部 Skill 标为 `validated`，且满足下文证据条件。

初始能力范围：身体力学包含步态与坐站；物体交互包含搬运和工具动作；角色表演包含视线、节奏与情绪。面部、四足及其他身体结构待有对应制作 case 后扩展，不预先声明支持。

## 固定输入

`assets.json` 使用对象，以稳定资产 ID 为键。每个值包含：

- `path`：仓库内 `.artifacts/inputs/` 下的相对文件路径。
- `sha256`：实际文件的 SHA-256。
- `source`：来源、生成方式和已知限制，不保存临时签名 URL。

原始大文件不提交 Git。换机器时从记录的来源恢复到同一路径，再执行 `check --artifacts`。初始可复用资产来自已有 winter-survival Meshy 角色；它的外观与绑定不代表已达到动画质量标准。

输入里已有的动作只能按 case 明确允许的方式使用。比较 Skill 制作能力时，固定 Meshy 产物；评测素材选型能力时，另外记录候选和服务版本。

## Case 定义

每个 `cases/<id>/case.json` 描述一个完整的实际制作任务：

```text
id                 kebab-case，等于目录名
skill              主负责 Skill；组合知识写在任务要求中
split              development 或 transfer
title              可读任务名称
prompt             可直接交给制作 Agent 的完整要求
inputs             assets.json 中的资产 ID 列表
scene              道具尺寸、位置、初始状态等固定条件
duration_seconds   目标片段时长
fps                目标采样帧率
camera             最终镜头与辅助视图
deliverables       必须交付的文件或视图
criteria           correctness 与 taste 两组标准
minimum_taste      接受作品所需的最低品味评分，1–5
required_for_release 是否属于本版本承诺覆盖的制作任务
```

每项标准包含唯一 `id` 和 `description`。正确性记录 `passed` 与依据；品味记录 1–5 分及依据。分数含义为：1 无法表达要求，2 明显欠缺，3 基本成立但有明显不足，4 达到任务要求，5 在任务要求内具有突出的表现。评价前按具体任务校准尺度，不能把评分当成客观物理量。

`development` 用于发现不足和提炼经验。`transfer` 用于从原始输入检查更新后的 Skill；它是公开的迁移任务，不自动构成盲测保留集。正式盲测应由评价者另行保管输入。

任务定义一旦开始执行，就通过 Git 固定版本。变更任务要求或固定输入时创建新的 case ID，并保留旧任务和记录；检查工具拒绝把已有记录关联到改写后的任务。

## 一次运行的记录

执行 `python3 tools/project.py new-run <case-id> <run-id>`，创建 `cases/<id>/runs/<run-id>.json` 后填写；无 Skill 基线加 `--without-skills`。命令以 `templates/run.json` 为模板，只建立待填写记录。记录：

- case、Skill 和输入资产的内容指纹。
- 模型、harness、Blender、预算及实际人工帮助。
- 初稿的 `.blend`、导出物与原速视频，逐项记录路径和 SHA-256。
- 具体不足、有效修改、修改者及理由。
- 修正版的同类产物和评价。
- 关联经验记录。

`status` 为 `recording` 或 `reviewed`。`initial` 和 `corrected` 各包含 `artifacts`、`review`；没有修正版时允许 `corrected` 为 `null`。`review` 包含 `verdict`（pending、accepted、rejected）、`reviewer`、`correctness`、`taste` 和 `remaining_issues`。

产物路径只使用 `.artifacts/` 下的仓库相对路径。必需产物角色为 `blend`、`export`、`video`。`correctness` 和 `taste` 以 case 的标准 ID 为键；每项都要有具体证据。接受记录需要完整覆盖标准、正确性全部通过、品味达到该 case 的下限，以及明确的评价者。

具体字段如下：

| 字段 | 填写要求 |
| --- | --- |
| `fingerprints.case` | case JSON 按键排序、无空白序列化后的 SHA-256；由 `new-run` 计算 |
| `fingerprints.skills` | 完整安装集的包内容指纹；基线为空对象。指纹由包内相对路径与文件哈希计算，不受修改时间影响 |
| `fingerprints.inputs` | 资产 ID 到原始文件 SHA-256 的映射 |
| `environment` | `model`、`harness`、`blender` 写实际版本；`budget` 写时间、token、服务调用等限制，`usage` 写实际消耗。未计量的部分明确说明 |
| `execution` | `from_raw_inputs`、`human_artifact_edits`、`human_extra_guidance` 填布尔值，`notes` 说明具体帮助或没有帮助 |
| `artifacts[]` | 每项有 `role`、`path`、`sha256`；其他辅助文件可用 `other` 角色 |
| `review.correctness.<id>` | `passed` 布尔值与 `evidence` 文本，定位视图、时间点或重新导入检查 |
| `review.taste.<id>` | `score` 为 1–5 整数，`evidence` 说明具体表演选择及效果 |
| `changes[]` | 每项有 `issue`、`change`、`actor`、`rationale`，包括失败尝试及其结果 |
| `lessons` | 关联经验记录 ID 的数组 |

接受作品的产物文件名须覆盖 case 的 `deliverables`。初稿与修正版使用不同目录，禁止复用路径覆盖初稿。`check` 校验结构；`check --artifacts` 另外核对输入及所有已记录产物的字节指纹，不解析媒体质量。补齐原速视频和观看评价是制作与评价者的责任。

首稿没有不足时不制造失败案例；修正尚未确认时保持 pending。历史作品可以导入，但必须注明未知变量及未获得确认的结论。

## 经验进入 Skill

将 `templates/lesson.json` 复制到 `lessons/<id>.json`。记录来源 case 与 run、观察到的问题、有效修改、适用条件、局限和修改的 Skill 文件。

`candidate` 经验可以作为明确标注的研究假设。`promoted` 经验需要来源作品的接受评价，目标文件实际存在，并在登记为 `transfer` 的任务中获得独立初稿的接受评价。独立保留任务由评价者另行管理；要纳入本工具检查，需在评测后导入同格式任务与记录。

`source` 和 `transfer_evidence[]` 中每项用 `case`、`run` 定位记录。`targets` 填仓库相对 Skill 文件路径。提升经验时，将迁移运行中对应 Skill 的指纹填入 `validated_skill_sha256`，保留这次验证针对的版本；以后修改 Skill 不改写历史证据。正式发布另外检查整个当前安装集的迁移结果。

根据经验内容选择落地位置：

| 内容 | 位置 |
| --- | --- |
| 通用制作选择 | `SKILL.md` |
| 任务、体型或风格分支 | `references/` |
| 可重复且易算错的操作 | `scripts/` |
| 确认优秀的姿势、曲线与动作 | `assets/` |

初稿与修正版的对照证明作品改进。更新 Skill 后，从原始输入重新制作的结果，才用于判断能力是否提升。不要将修正版工程直接作为新版本的起点。

## 发布

`python3 tools/project.py package` 只接受带预发布后缀的版本号，生成各 Skill 的独立 ZIP、发布清单和 SHA-256 校验文件。清单注明成熟度和源码指纹；草案不能被包装成已验证能力。

输出位于 `dist/<version>/`，相同源码产生相同包内容；版本目录已存在时拒绝覆盖。调整内容后更新版本号。打包只接收 `SKILL.md` 及 `references/`、`scripts/`、`assets/`；拒绝符号链接、缺失引用及跨包引用，忽略隐藏文件和 Python 缓存。完整 case、经验记录与原始模型留在工程中。

正式打包使用 `python3 tools/project.py package --release`，需要：

1. 工程版本是正式版本号。
2. 所有 Skill 的成熟度为 `validated`。
3. 每个必需的 development case 有使用对应 Skill 的已接受作品；每个必需的 transfer case 有使用当前完整 Skill 集重新制作的已接受初稿。
4. 迁移记录没有人工修改作品或追加制作指导；环境与预算如实记录。
5. 接受记录的 case、输入和产物指纹可核对，本地证据文件可读取。
6. 每个 Skill 至少有一个 development 和一个 transfer case。

发布前运行工程检查、测试和正式打包。然后提交版本修改，为该提交创建版本标签，将 ZIP、清单和校验文件上传到选定的 Git 托管平台。具体命令见 [发布说明](release.md)；本工程不自动选择远端仓库，也不自动推送。

CI 运行结构检查和工具测试；实际制作评价以及需要本地动画产物的正式发布检查由有素材的制作环境执行。CI 通过不表示动画质量通过。

安装时，将单个 ZIP 解压后得到的 `<skill-name>/` 放入目标产品的 Skill 目录。TRAE 项目级目录为 `.trae/skills/`；CN 用户级目录为 `~/.trae-cn/skills/`。检查同名目录后再安装，不自动覆盖已有安装。
