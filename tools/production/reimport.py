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
max_prop_error = 0
max_grip_error = 0
prop_name = {"wide-crate-transfer": "wide-crate", "lift-heavy-box": "box", "axe-strike": "Axe"}.get(out.parent.name)
prop = bpy.data.objects.get(prop_name) if prop_name else None
scale = json.loads((out / "production.json").read_text())["normalization"]["scale"]
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
    if prop is not None:
        max_prop_error = max(max_prop_error, (prop.matrix_world.translation-Vector(sample["prop_center"])).length)
    if sample.get("grip_weight", 0) > .999:
        for i, side in enumerate(("L", "R")):
            hand = arm.pose.bones["Hand."+side]
            palm = arm.matrix_world @ (hand.matrix @ Vector((0,.07/scale,0)))
            max_grip_error = max(max_grip_error, (palm-Vector(sample["grip_targets"][i])).length)
    right_foot_positions.append(arm.matrix_world @ arm.pose.bones["Foot.R"].head)
    left_foot_positions.append(arm.matrix_world @ arm.pose.bones["Foot.L"].head)
right_drift = max((v - right_foot_positions[0]).length for v in right_foot_positions)
left_delta = left_foot_positions[-1] - left_foot_positions[0]
result = {
    "frames": len(samples), "bone_count": len(arm.pose.bones),
    "exported_seconds": (action.frame_range[1] - action.frame_range[0]) / 30,
    "max_joint_position_error_m": max_error,
    "max_prop_position_error_m": max_prop_error,
    "max_palm_target_error_m": max_grip_error,
    "right_ankle_world_drift_m": right_drift,
    "left_ankle_final_displacement_m": list(left_delta),
    "measurement_limit": "Joint positions; shoe deformation and seat contact require image review.",
}
(out / "reimport-check.json").write_text(json.dumps(result, indent=2))
print("REIMPORT", json.dumps(result))
assert max_error < .0001
assert max_prop_error < .0001
assert max_grip_error < .0001
assert len(arm.pose.bones) == 17
