"""Case-authoring utilities for the fixed survivor rig; run with Blender Python."""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]


def curve(t, keys):
    """Monotone cubic Hermite interpolation, with flat holds and no overshoot."""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    slopes = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(keys, keys[1:])]
    tangents = [0.0]
    for a, b in zip(slopes, slopes[1:]):
        tangents.append(0 if a * b <= 0 else 2 * a * b / (a + b))
    tangents.append(0.0)
    for i, (a, b) in enumerate(zip(keys, keys[1:])):
        if a[0] <= t <= b[0]:
            h = b[0] - a[0]
            u = (t - a[0]) / h
            return ((2*u**3 - 3*u**2 + 1)*a[1] + (u**3 - 2*u**2 + u)*h*tangents[i]
                    + (-2*u**3 + 3*u**2)*b[1] + (u**3 - u**2)*h*tangents[i+1])


class Rig:
    def __init__(self, case_id, version="initial"):
        if "--" in sys.argv:
            version = sys.argv[sys.argv.index("--") + 1]
        if not version or Path(version).name != version or version in {".", ".."}:
            raise ValueError("Revision must be a directory name")
        self.case_id = case_id
        self.case = json.loads((ROOT / "cases" / case_id / "case.json").read_text())
        self.out = ROOT / ".artifacts" / "production" / case_id / version
        if (self.out / "editable.blend").exists() or (self.out / "animation.glb").exists():
            raise FileExistsError("Keep existing evidence; pass -- <new-revision> after the script")
        self.out.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / ".artifacts/inputs/survivor-rig.glb"))
        self.arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        self.mesh = bpy.data.objects["Mesh_0"]
        for obj in list(bpy.data.objects):
            if obj not in {self.arm, self.mesh}:
                bpy.data.objects.remove(obj, do_unlink=True)
        self.arm.animation_data_clear()
        for action in list(bpy.data.actions):
            bpy.data.actions.remove(action)
        for bone in self.arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
            bone.rotation_mode = "QUATERNION"
        bpy.context.view_layer.update()
        zs = [v.co.z for v in self.mesh.data.vertices]
        self.scale = 1.8 / (max(zs) - min(zs))
        self.floor = min(zs)
        # Source forward is -Y. Parent transform preserves the original bind matrices.
        root = bpy.data.objects.new("CharacterSpace", None)
        bpy.context.collection.objects.link(root)
        root.rotation_euler.z = math.pi
        root.scale = (self.scale,) * 3
        root.location.z = -self.floor * self.scale
        self.arm.parent = root
        self.scene = bpy.context.scene
        self.scene.render.fps = self.case["fps"]
        self.scene.frame_start = 1
        self.scene.frame_end = 1 + round(self.case["duration_seconds"] * self.case["fps"])
        self.previous = {}
        self.samples = []
        self.build_bench()

    def local(self, p):
        return Vector((-p[0] / self.scale, -p[1] / self.scale, p[2] / self.scale + self.floor))

    def world(self, p):
        return self.arm.matrix_world @ p

    def aim(self, name, end):
        pb = self.arm.pose.bones[name]
        start = pb.head.copy()
        rest = pb.bone
        rot = (rest.tail_local - rest.head_local).rotation_difference(end - start)
        matrix = rot.to_matrix().to_4x4() @ rest.matrix_local
        matrix.translation = start
        pb.matrix = matrix
        bpy.context.view_layer.update()

    def pose(self, pelvis, lean, feet, arm_forward=0.12, arm_bend=0.1, roll=0):
        bones = self.arm.pose.bones
        for bone in bones:
            bone.matrix_basis = Matrix.Identity(4)
        hips = bones["Hips"]
        m = Matrix.Rotation(math.radians(roll), 4, "Y") @ hips.bone.matrix_local
        m.translation = self.local(pelvis)
        hips.matrix = m
        bpy.context.view_layer.update()
        # Distribute torso flexion, with restrained head counter-rotation.
        for name, angle in (("Spine", lean * .65), ("Chest", lean), ("Neck", lean * .66), ("Head", lean * .5)):
            pb = bones[name]
            m = Matrix.Rotation(math.radians(angle), 4, "X") @ pb.bone.matrix_local
            m.translation = pb.head
            pb.matrix = m
            bpy.context.view_layer.update()
        for side, foot in zip(("L", "R"), feet):
            thigh = bones["Thigh." + side]
            shin = bones["Shin." + side]
            hip = thigh.head.copy()
            ankle = self.local(foot)
            length_a, length_b = thigh.bone.length, shin.bone.length
            ray = ankle - hip
            d = ray.length
            assert abs(length_a - length_b) < d < length_a + length_b, (self.scene.frame_current, d)
            axis = ray.normalized()
            pole = Vector((0, -1, 0))
            pole = (pole - axis * pole.dot(axis)).normalized()
            along = (length_a**2 - length_b**2 + d**2) / (2*d)
            knee = hip + axis * along + pole * math.sqrt(max(0, length_a**2 - along**2))
            self.aim(thigh.name, knee)
            self.aim(shin.name, ankle)
            pb = bones["Foot." + side]
            m = pb.bone.matrix_local.copy()
            m.translation = ankle
            pb.matrix = m
            bpy.context.view_layer.update()
            sign = 1 if side == "L" else -1
            upper = bones["UpperArm." + side]
            self.aim(upper.name, upper.head + Vector((sign * .19, -arm_forward, -1)))
            fore = bones["Forearm." + side]
            self.aim(fore.name, fore.head + Vector((sign * .04, -(arm_forward + arm_bend), -1)))
            hand = bones["Hand." + side]
            self.aim(hand.name, hand.head + Vector((sign * .02, -(arm_forward + arm_bend), -1)))
        for pb in bones:
            q = pb.rotation_quaternion
            if pb.name in self.previous and self.previous[pb.name].dot(q) < 0:
                q.negate()
            self.previous[pb.name] = q.copy()
            pb.keyframe_insert("location")
            pb.keyframe_insert("rotation_quaternion")
        self.samples.append({
            "frame": self.scene.frame_current,
            "pelvis": list(self.world(hips.head)),
            "feet": [list(self.world(bones["Foot." + s].head)) for s in ("L", "R")],
            "knees": [list(self.world(bones["Shin." + s].head)) for s in ("L", "R")],
        })

    def build_bench(self):
        prop = self.case["scene"]["props"][0]
        w, d, thick = prop["seat_dimensions"]
        x, y = prop["seat_center_xy"]
        z = prop["seat_top_z"]
        mat = bpy.data.materials.new("Warm oak")
        mat.diffuse_color = (.24, .12, .052, 1)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = mat.diffuse_color
        bsdf.inputs["Roughness"].default_value = .73
        def cube(name, loc, dim):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
            obj = bpy.context.object
            obj.name = name
            obj.dimensions = dim
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            obj.data.materials.append(mat)
            bevel = obj.modifiers.new("Soft timber edges", "BEVEL")
            bevel.width, bevel.segments = .008, 3
            return obj
        cube("Seat", (x, y, z-thick/2), (w, d, thick))
        for sx in (-1, 1):
            for sy in (-1, 1):
                cube("Bench leg", (x+sx*(w/2-.05), y+sy*(d/2-.05), (z-thick)/2),
                     (.065, .065, z-thick))
        cube("Bench brace", (x, y, .13), (w-.08, .045, .05))

    def camera(self, name, location, target):
        data = bpy.data.cameras.new(name)
        obj = bpy.data.objects.new(name, data)
        self.scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
        data.type, data.ortho_scale = "ORTHO", 3.25
        return obj

    def finish(self, name, notes):
        action = self.arm.animation_data.action
        action.name = name
        for slot in action.slots:
            for layer in action.layers:
                for strip in layer.strips:
                    bag = strip.channelbag(slot)
                    if bag:
                        for fc in bag.fcurves:
                            for key in fc.keyframe_points:
                                key.interpolation = "LINEAR"
        self.scene.frame_set(1)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in self.scene.objects:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=str(self.out / "animation.glb"), export_format="GLB",
            use_selection=True, export_animations=True, export_animation_mode="ACTIONS",
            export_force_sampling=True, export_frame_range=True,
            export_anim_slide_to_zero=True,
            export_skins=True, export_def_bones=True, export_cameras=False, export_lights=False)
        self.scene.render.engine = "BLENDER_EEVEE"
        self.scene.render.resolution_x = 1920
        self.scene.render.resolution_y = 1080
        self.scene.render.resolution_percentage = 100
        self.scene.world.color = (.25, .25, .25)
        self.scene.view_settings.view_transform = "AgX"
        bpy.ops.mesh.primitive_plane_add(size=200)
        floor = bpy.context.object
        floor.name = "Preview ground"
        floor.data.materials.append(bpy.data.materials.new("Ground"))
        floor.data.materials[0].diffuse_color = (.28, .32, .3, 1)
        for loc, power, size in (((-3, 4, 6), 1100, 5), ((4, 1, 4), 900, 4)):
            data = bpy.data.lights.new("Softbox", "AREA")
            data.energy, data.shape, data.size = power, "DISK", size
            light = bpy.data.objects.new(data.name, data)
            self.scene.collection.objects.link(light)
            light.location = loc
            light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
        self.scene.camera = self.camera("Main", (-3.4, 5, 2.8), (0, .2, .9))
        self.camera("Side", (-5, .2, 1.1), (0, .2, .95))
        self.scene["production_notes"] = notes
        bpy.ops.wm.save_as_mainfile(filepath=str(self.out / "editable.blend"))
        (self.out / "motion-samples.json").write_text(json.dumps(self.samples, indent=2))
        (self.out / "production.json").write_text(json.dumps({
            "case": self.case_id, "clip": name, "fps": self.scene.render.fps,
            "seconds": self.case["duration_seconds"], "source_actions_reused": False,
            "normalization": {"scale": self.scale, "rotate_z_degrees": 180,
                              "translate_z": -self.floor*self.scale},
            "notes": notes,
        }, ensure_ascii=False, indent=2))
        print("PRODUCTION", self.out)
