"""Register the seven September 28 productions; keep artistic review pending."""
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project

SCRIPTS = {
    "wide-crate-transfer": "wide_crate.py", "relief-transfer": "relief.py",
    "walk-turn-stop": "walk_turn.py", "tired-walk": "tired_walk.py",
    "lift-heavy-box": "heavy_box.py", "axe-strike": "axe.py", "alert-turn": "alert.py",
}
OBSERVATIONS = {
    "wide-crate-transfer": [
        "抓握、抬起、左转和低台放置已有预览；粗手部网格不能表达手指包握。",
        "工程首稿注释中的接触起点 1.6 秒是预演旧值；motion-samples.json 的完整握持实际从约 1.95 秒开始。",
    ],
    "relief-transfer": ["头胸朝向、呼气与手臂松开已有预览；紧张转为安心的可辨认程度待独立评价。"],
    "walk-turn-stop": ["保留初稿持续屈膝的画面；修正版按双脚可达范围抬高经过阶段骨盆。",
                       "没有脚趾关节，脚掌滚动与服装变形仍有限。"],
    "tired-walk": ["保留初稿过低骨盆；修正版减少持续下蹲，疲劳主要由短步、躯干与恢复呼吸表达。"],
    "lift-heavy-box": ["箱底在 0.75 m 台面稳定后松手；手指未绑定，握持近景仍有局部网格穿插。",
                       "20 kg 重量感属于表演意图，尚无独立品味评分。"],
    "axe-strike": ["刃部目标接触位于 2.9 秒；双手固定在柄部，粗手掌不能形成完整包握。",
                   "不含木材破碎、动态衣物或刚体冲击模拟。"],
    "alert-turn": ["刺激后头部先转、身体随后换脚朝右后方；缺少眼球骨，方向依靠头部表达。"],
}

for case_id, script in SCRIPTS.items():
    path = project.ROOT / "cases" / case_id / "runs/20260928-first-motion.json"
    run = project.load(path)
    run["environment"] = {
        "model": "GPT-6", "harness": "TRAE agent; Blender CLI; Three.js viewer with Playwright/Chrome",
        "blender": "5.1.1 (b70da489d7f4)",
        "budget": "本地制作；未设固定时间或 token 预算；未调用收费生成。",
        "usage": "0 次收费生成；未单独计量 token 和制作耗时。最终视频由逐帧采样合成，信息见各镜头 rendering.json；recording.json 为实时捕获诊断历史。",
    }
    run["execution"] = {
        "from_raw_inputs": True, "human_artifact_edits": False, "human_extra_guidance": False,
        "notes": "用户要求制作剩余 7 例，没有提供关键帧、姿势或人工作品修改。"
                 "本轮先从原始 GLB 制作宽箱与放松两个迁移案例，完成其初稿前未读取其他案例的成品关键帧或评价。"
                 "复用原有坐标归一化与骨骼求解工具，并扩展双手 IK；各任务重新编写节拍和轨迹。"
                 "同时读取全局 animated-character-pipeline 的通用资产、运动和验收参考；它未纳入三个被测 Skill 的包指纹。"
                 "未复用输入 Idle、Walk、Chop。公开任务、同一 Agent 和同一骨架，不构成盲测或 Skill 效果对照实验。",
    }
    for version in ("initial", "corrected"):
        folder = project.ROOT / ".artifacts/production" / case_id / version
        if not (folder / "animation.glb").exists():
            continue
        for source, filename in ((Path(__file__).with_name(script), "authoring.py"),
                                 (Path(__file__).with_name("rig.py"), "rig.py")):
            if not (folder / filename).exists():
                shutil.copyfile(source, folder / filename)
        artifacts = []
        for file in sorted(folder.iterdir()):
            if file.suffix not in {".blend", ".glb", ".mp4", ".json", ".py", ".png"}:
                continue
            role = {".blend": "blend", ".glb": "export", ".mp4": "video"}.get(file.suffix, "other")
            artifacts.append({"role": role, "path": file.relative_to(project.ROOT).as_posix(),
                              "sha256": project.file_hash(file)})
        correctness = {}
        check_path = folder / "reimport-check.json"
        if check_path.exists() and case_id != "relief-transfer":
            check = project.load(check_path)
            correctness["export"] = {
                "passed": check["max_joint_position_error_m"] < .0001 and check["max_prop_position_error_m"] < .0001,
                "evidence": f"reimport-check.json：{check['frames']} 帧，{check['bone_count']} 骨，"
                            f"{check['exported_seconds']} 秒；最大关节回读误差 "
                            f"{check['max_joint_position_error_m']:.2g} m，道具误差 "
                            f"{check['max_prop_position_error_m']:.2g} m。只证明导出回读一致性。",
            }
        run[version] = {"artifacts": artifacts, "review": {
            "verdict": "pending", "reviewer": "GPT-6（制作及技术检查；非独立品味评价者）",
            "correctness": correctness, "taste": {},
            "remaining_issues": OBSERVATIONS[case_id] + [
                "待独立原速评价。骨骼与掌心指标不等于蒙皮接触或动作自然度通过；Skill 保持 draft。"],
        }}
    run["changes"] = []
    if case_id in {"walk-turn-stop", "tired-walk"}:
        run["changes"] = [{
            "issue": "初稿骨盆持续偏低，行走或恢复阶段有持续蹲行观感。",
            "change": ("依据脚部可达范围抬高经过姿势，保留步幅、路径和接触时刻。"
                       if case_id == "walk-turn-stop" else "提高行走与喘息阶段骨盆，保留短步和胸腔呼吸节奏。"),
            "actor": "GPT-6", "rationale": "依据初稿 Three.js 预览；保留 initial，并另存 corrected 工程和导出物。",
        }]
    elif case_id in {"wide-crate-transfer", "lift-heavy-box", "axe-strike"}:
        run["changes"] = [{
            "issue": "导出前的 IK 可达检查发现部分姿势超出固定臂长。",
            "change": {"wide-crate-transfer": "降低取箱骨盆、推迟伸手、提前箱体上升。",
                       "lift-heavy-box": "侧移末段让身体靠近台面。",
                       "axe-strike": "工具回收时减小前伸并保留胸腔前倾。"}[case_id],
            "actor": "GPT-6", "rationale": "保留骨长；这些是首个可导出初稿之前的预演修正，不是已评价作品的对照。",
        }]
    if list((project.ROOT / ".artifacts/production" / case_id).glob("*/main-first-take.mp4")):
        run["changes"].append({
            "issue": "查看器截断帧间隔或沿用暂停前计时，录制器又晚于播放首帧启动，导致时长偏差或首帧缺失。",
            "change": "修正查看器计时；实时录屏仍有丢帧，最终按任务帧率逐帧采样 GLB 并以同帧率编码。保留全部捕获历史。",
            "actor": "GPT-6", "rationale": "原速评分使用 main.mp4 等逐帧视频及 rendering 记录；realtime、first-take、capture 视频仅用于诊断。GLB 未修改。",
        })
    project.write(path, run)
    print(path.relative_to(project.ROOT))
