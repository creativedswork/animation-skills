"""One two-handed strike, authored around the actual cutting edge."""
import sys
import math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rig import Rig,curve as c
import bpy
from mathutils import Vector,Matrix

r=Rig("axe-strike")
stump=r.case["scene"]["props"][1]
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=stump["radius"],depth=stump["top_z"],
                                  location=(0,.85,.275))
wood=bpy.context.object
wood.name="Stump"
wood.data.materials.append(r.cube("Temporary material",(0,0,-10),(.01,)*3).data.materials[0])
bpy.data.objects.remove(bpy.data.objects["Temporary material"],do_unlink=True)
tool=bpy.data.objects.new("Axe",None)
r.scene.collection.objects.link(tool)
r.cube("Axe handle",(0,0,.4),(.038,.042,.8),(.16,.073,.027,1),tool)
# The lower forward edge of this wedge is the measured contact point.
vertices=[(-.045,-.08,.67),(.045,-.08,.67),(-.045,-.08,.83),(.045,-.08,.83),
          (-.012,.16,.78),(.012,.16,.78)]
mesh=bpy.data.meshes.new("Steel wedge")
mesh.from_pydata(vertices,[],[(0,1,3,2),(0,4,5,1),(2,3,5,4),(0,2,4),(1,5,3)])
blade=bpy.data.objects.new("Axe blade",mesh)
r.scene.collection.objects.link(blade)
blade.parent=tool
steel=bpy.data.materials.new("Steel")
steel.diffuse_color=(.32,.36,.38,1)
steel.use_nodes=True
steel.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=steel.diffuse_color
steel.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value=.8
steel.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=.32
blade.data.materials.append(steel)
edge=Vector((0,.16,.78))
impact_rotation=Matrix.Rotation(math.radians(-110),3,"X")
contact_origin=Vector((0,.85,.55))-impact_rotation@edge
for frame in range(1,r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t=(frame-1)/30
    angle=c(t,[(0,-38),(.65,-38),(1.65,17),(2.25,22),(2.48,5),(2.7,-58),
                (2.90,-110),(3.12,-110),(3.42,-104),(4.4,-70),(5.4,-48),(6,-48)])
    rotation=Matrix.Rotation(math.radians(angle),3,"X")
    origin=Vector((0,c(t,[(0,.22),(.65,.22),(1.8,.38),(2.3,.38),
                          (2.9,contact_origin.y),(3.12,contact_origin.y),(4.4,.16),(6,.20)]),
                    c(t,[(0,.96),(.65,.96),(1.8,1.40),(2.3,1.40),
                          (2.9,contact_origin.z),(3.12,contact_origin.z),(4.4,1.00),(6,.98)])))
    tool.location=origin
    tool.rotation_euler.x=math.radians(angle)
    tool.keyframe_insert("location")
    tool.keyframe_insert("rotation_euler")
    grips=[origin+rotation@Vector((0,0,z)) for z in (.14,.32)]
    r.pose((0,c(t,[(0,-.03),(2.3,-.05),(2.9,.03),(3.1,.035),(4.4,-.02)]),
            c(t,[(0,.79),(1.9,.82),(2.3,.815),(2.9,.65),(3.1,.645),(4.4,.77),(6,.79)])),
           c(t,[(0,5),(1.8,-6),(2.3,-8),(2.9,38),(3.1,40),(4.4,22),(6,8)]),
           [(-.16,.03,.13146),(.16,-.15,.13146)],hands=grips,
           hand_dirs=[(1,0,0),(-1,0,0)],head_pitch=c(t,[(0,12),(2.3,0),(2.9,24),(6,12)]))
    r.samples[-1].update(prop_center=list(origin),edge=list(origin+rotation@edge),
                         grip_targets=[list(p) for p in grips],grip_weight=1)
r.finish("AxeSingleStrike", "One strike; wedge cutting edge hits (0,0.85,0.55) at 2.9 s. "
         "Hold to 3.12 s, withdraw and recover on a shorter arc. Both palms follow fixed handle "
         "points. No Chop keys reused; no finger curl, wood fracture or rigid-body simulation.")
