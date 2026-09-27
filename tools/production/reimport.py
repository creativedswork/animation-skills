"""Verify exported deformation-bone positions against every authored sample."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
samples = json.loads((out / "motion-samples.json").read_text())
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=str(out / "animation.glb"))
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
action = arm.animation_data.action
max_error = 0
right_foot_positions = []
left_foot_positions = []
for sample in samples:
    bpy.context.scene.frame_set(sample["frame"] - 1)
    bpy.context.view_layer.update()
    mapping = [("Hips", sample["pelvis"])]
    mapping += [(f"Foot.{side}", sample["feet"][i]) for i, side in enumerate(("L", "R"))]
    mapping += [(f"Shin.{side}", sample["knees"][i]) for i, side in enumerate(("L", "R"))]
    for name, expected in mapping:
        actual = arm.matrix_world @ arm.pose.bones[name].head
        max_error = max(max_error, (actual - Vector(expected)).length)
    right_foot_positions.append(arm.matrix_world @ arm.pose.bones["Foot.R"].head)
    left_foot_positions.append(arm.matrix_world @ arm.pose.bones["Foot.L"].head)
right_drift = max((v - right_foot_positions[0]).length for v in right_foot_positions)
left_delta = left_foot_positions[-1] - left_foot_positions[0]
result = {
    "frames": len(samples), "bone_count": len(arm.pose.bones),
    "exported_seconds": (action.frame_range[1] - action.frame_range[0]) / 30,
    "max_joint_position_error_m": max_error,
    "right_ankle_world_drift_m": right_drift,
    "left_ankle_final_displacement_m": list(left_delta),
    "measurement_limit": "Joint positions; shoe deformation and seat contact require image review.",
}
(out / "reimport-check.json").write_text(json.dumps(result, indent=2))
print("REIMPORT", json.dumps(result))
assert max_error < .0001
assert right_drift < .0001
assert len(arm.pose.bones) == 17
