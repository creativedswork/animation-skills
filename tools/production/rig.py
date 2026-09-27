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


def turn(p, degrees):
    return Matrix.Rotation(math.radians(degrees), 3, "Z") @ Vector(p)


def step(t, start, end, a, b, height=.065):
    """A single authored swing; endpoints remain stationary outside its interval."""
    u = max(0, min(1, (t-start)/(end-start)))
    v = u*u*(3-2*u)
    p = Vector(a).lerp(Vector(b), v)
    p.z += height * math.sin(math.pi*u)**2
    return p


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
        if any("seat_dimensions" in p for p in self.case["scene"]["props"]):
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

    def solve(self, upper, lower, end, pole):
        a, b = self.arm.pose.bones[upper], self.arm.pose.bones[lower]
        start = a.head.copy()
        ray = end-start
        d, la, lb = ray.length, a.bone.length, b.bone.length
        if not abs(la-lb) < d < la+lb:
            raise ValueError((self.scene.frame_current, upper, "unreachable", d, la+lb,
                              tuple(self.world(start)), tuple(self.world(end))))
        axis = ray.normalized()
        bend = (pole-axis*pole.dot(axis)).normalized()
        along = (la*la-lb*lb+d*d)/(2*d)
        joint = start+axis*along+bend*math.sqrt(max(0, la*la-along*along))
        self.aim(upper, joint)
        self.aim(lower, end)

    def pose(self, pelvis, lean, feet, arm_forward=0.12, arm_bend=0.1, roll=0,
             yaw=0, foot_yaws=None, chest_yaw=None, head_yaw=None, head_pitch=None,
             hands=None, hand_dirs=None, hand_weights=None):
        bones = self.arm.pose.bones
        for bone in bones:
            bone.matrix_basis = Matrix.Identity(4)
        hips = bones["Hips"]
        rotation = Matrix.Rotation(math.radians(yaw), 4, "Z")
        m = rotation @ Matrix.Rotation(math.radians(roll), 4, "Y") @ hips.bone.matrix_local
        m.translation = self.local(pelvis)
        hips.matrix = m
        bpy.context.view_layer.update()
        # Distribute torso flexion, with restrained head counter-rotation.
        for name, angle in (("Spine", lean * .65), ("Chest", lean), ("Neck", lean * .66), ("Head", lean * .5)):
            pb = bones[name]
            heading = yaw if chest_yaw is None else chest_yaw
            if name in {"Neck", "Head"}:
                heading = heading if head_yaw is None else head_yaw
            if name == "Head" and head_pitch is not None:
                angle = head_pitch
            m = (Matrix.Rotation(math.radians(heading), 4, "Z")
                 @ Matrix.Rotation(math.radians(angle), 4, "X") @ pb.bone.matrix_local)
            m.translation = pb.head
            pb.matrix = m
            bpy.context.view_layer.update()
        for i, (side, foot) in enumerate(zip(("L", "R"), feet)):
            ankle = self.local(foot)
            self.solve("Thigh."+side, "Shin."+side, ankle, turn((0, -1, 0), yaw))
            pb = bones["Foot." + side]
            fy = yaw if foot_yaws is None else foot_yaws[i]
            m = Matrix.Rotation(math.radians(fy), 4, "Z") @ pb.bone.matrix_local
            m.translation = ankle
            pb.matrix = m
            bpy.context.view_layer.update()
            sign = 1 if side == "L" else -1
            upper = bones["UpperArm." + side]
            af = arm_forward[i] if isinstance(arm_forward, (list, tuple)) else arm_forward
            ab = arm_bend[i] if isinstance(arm_bend, (list, tuple)) else arm_bend
            self.aim(upper.name, upper.head + turn((sign*.19, -af, -1), yaw))
            fore = bones["Forearm." + side]
            self.aim(fore.name, fore.head + turn((sign*.04, -(af+ab), -1), yaw))
            hand = bones["Hand." + side]
            self.aim(hand.name, hand.head + turn((sign*.02, -(af+ab), -1), yaw))
            if hands and hands[i] is not None:
                direction = Vector(hand_dirs[i]).normalized()
                # Palm center is 7 cm along the hand, not the artificial bone tail.
                desired = self.local(Vector(hands[i])-direction*.07)
                weight = 1 if hand_weights is None else hand_weights[i]
                wrist = hand.head.lerp(desired, weight)
                self.solve(upper.name, fore.name, wrist, turn((sign, .3, -.3), yaw))
                local_direction = Vector((-direction.x, -direction.y, direction.z))
                current_direction = (hand.tail-hand.head).normalized()
                self.aim(hand.name, hand.head+current_direction.lerp(local_direction, weight))
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
            "palms": [list(self.world(bones["Hand."+s].head +
                      (bones["Hand."+s].tail-bones["Hand."+s].head).normalized()*(.07/self.scale)))
                      for s in ("L", "R")],
        })

    def cube(self, name, location, dimensions, color=(.28, .15, .065, 1), parent=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.name, obj.dimensions = name, dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mat = bpy.data.materials.new(name)
        mat.diffuse_color, mat.use_nodes = color, True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = .7
        obj.data.materials.append(mat)
        bevel = obj.modifiers.new("Edge bevel", "BEVEL")
        bevel.width, bevel.segments = .005, 2
        obj.parent = parent
        return obj

    def table(self, prop):
        w, d, thick = prop["top_dimensions"]
        x, y = prop["center_xy"]
        z = prop["top_z"]
        self.cube(prop["name"], (x, y, z-thick/2), (w, d, thick))
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.cube("Table leg", (x+sx*(w/2-.05), y+sy*(d/2-.05), (z-thick)/2),
                          (.065, .065, z-thick))

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
        for obj in self.scene.objects:
            if not obj.animation_data or not obj.animation_data.action:
                continue
            action = obj.animation_data.action
            action.name = name if obj == self.arm else name+" "+obj.name
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
            use_selection=True, export_animations=True, export_animation_mode="ACTIVE_ACTIONS",
            export_nla_strips_merged_animation_name=name,
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
