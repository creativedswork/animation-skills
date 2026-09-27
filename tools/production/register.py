"""Register this production session's files without asserting artistic acceptance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project

for case_id in ("low-seat-transfer", "sit-stand"):
    path = project.ROOT / "cases" / case_id / "runs/20260926-first-motion.json"
    run = project.load(path)
    run["environment"] = {
        "model": "GPT-6",
        "harness": "TRAE agent; local Blender CLI and Playwright/Chrome",
        "blender": "5.1.1 (b70da489d7f4)",
        "budget": "Local production only; no paid generation; no fixed time/token budget.",
        "usage": "0 Meshy or other paid generation calls. Tokens and active production time not metered.",
    }
    run["execution"] = {
        "from_raw_inputs": True,
        "human_artifact_edits": False,
        "human_extra_guidance": False,
        "notes": "用户指出两例没有动作并询问进度，未提供姿势、曲线或人工作品修改。"
                 "先从固定原始输入制作低凳任务，期间没有其他 case 的作品可读；"
                 "随后制作普通凳。共用骨骼求解代码，分别编写动作节拍，无源动作关键帧复用。"
                 "初稿与修正版保存在不同目录；没有独立品味评价或 Skill 能力提升结论。",
    }
    versions = ("initial", "corrected") if case_id == "low-seat-transfer" else ("initial",)
    for version in versions:
        folder = project.ROOT / ".artifacts/production" / case_id / version
        artifacts = []
        for file in sorted(folder.iterdir()):
            if file.suffix not in {".blend", ".glb", ".mp4", ".json", ".py"}:
                continue
            role = {".blend": "blend", ".glb": "export", ".mp4": "video"}.get(file.suffix, "other")
            artifacts.append({"role": role, "path": file.relative_to(project.ROOT).as_posix(),
                              "sha256": project.file_hash(file)})
        review = {"verdict": "pending", "reviewer": None, "correctness": {}, "taste": {},
                  "remaining_issues": ["待独立评价动作重量与节奏；未据此提升 Skill 成熟度。",
                                       "保留源角色蒙皮，未制作脚趾滚动或衣物碰撞。"]}
        if case_id == "low-seat-transfer" and version == "initial":
            review["remaining_issues"] = [
                "侧面 0 秒可见坐姿悬空；修正版将初始骨盆降低 0.08 m。",
                "GLB 时间从 1/30 秒开始，Three.js 显示 6.033333 秒；修正版移至零时刻。",
            ]
        run[version] = {"artifacts": artifacts, "review": review}
    if case_id == "low-seat-transfer":
        run["changes"] = [
            {"issue": "初稿坐姿与低凳座面有可见空隙。",
             "change": "初始骨盆从 0.445 m 降到 0.365 m，并衔接离座段的骨盆曲线。",
             "actor": "GPT-6", "rationale": "依据初稿与修正版 side-0.png 的实际网格接触调整。"},
            {"issue": "初稿导出包含一个空的起始帧间隔。",
             "change": "启用 glTF export_anim_slide_to_zero；动作在 Three.js 中为 6 秒。",
             "actor": "GPT-6", "rationale": "viewer-check.json 记录初稿 6.033333 秒、修正版 6 秒。"},
        ]
    project.write(path, run)
    print(path.relative_to(project.ROOT))
