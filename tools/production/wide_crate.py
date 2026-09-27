"""Independent wide-crate transfer, authored from the fixed raw rig."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve as c, turn, step
from mathutils import Vector
import math

r = Rig("wide-crate-transfer")
prop, table = r.case["scene"]["props"]
crate = r.cube("wide-crate", prop["center"], prop["dimensions"])
r.table(table)
for x in (-.405, .405):
    r.cube("Crate hand rail", (x, 0, .12), (.025, .23, .04), (.12, .065, .025, 1), crate)

for frame in range(1, r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t = (frame-1)/30
    yaw = c(t, [(0,0),(3.35,0),(4.2,42),(5.15,90),(8,90)])
    px = c(t, [(0,0),(3.3,0),(4.3,-.10),(5.3,-.23),(6.4,-.24),(8,-.16)])
    py = c(t, [(0,-.10),(1.5,-.04),(3.3,-.04),(4.4,.14),(5.3,.2),(8,.2)])
    pz = c(t, [(0,.80),(.45,.79),(1.6,.30),(2,.30),(3.1,.76),(5.3,.75),
               (6.35,.50),(6.9,.50),(7.8,.79),(8,.79)])
    lean = c(t, [(0,3),(.45,6),(1.6,65),(2,65),(3.1,12),(5.3,12),(6.35,42),
                 (6.9,42),(7.8,3)])
    if t <= 3.35:
        center = Vector((0, c(t,[(0,.5),(2,.5),(3.1,.41)]),
                         c(t,[(0,.15),(2,.15),(2.45,.48),(3.1,.89)])))
    else:
        center = Vector((px, py, 0))+turn((0,.45,.89),yaw)
        if t > 5.3:
            center = Vector((c(t,[(5.3,-.68),(6.35,-.80),(8,-.80)]),.2,
                             c(t,[(5.3,.89),(6.35,.60),(8,.60)])))
    crate.location, crate.rotation_euler.z = center, math.radians(yaw)
    crate.keyframe_insert("location")
    crate.keyframe_insert("rotation_euler")
    left = step(t,3.45,4.05,(-.13,-.1,.13146),(-.20,.13,.13146))
    left = step(t,4.65,5.2,left,(-.23,.07,.13146))
    right = step(t,4.08,4.62,(.13,-.1,.13146),(-.04,.34,.13146))
    fy = [c(t,[(0,0),(3.45,0),(4.05,45),(4.65,45),(5.2,90)]),
          c(t,[(0,0),(4.08,0),(4.62,90)])]
    grips = [center+turn((x,0,.12),yaw) for x in (-.405,.405)]
    weight = c(t,[(0,0),(1.55,0),(1.95,1),(6.75,1),(7.15,0),(8,0)])
    r.pose((px,py,pz),lean,[left,right],yaw=yaw,foot_yaws=fy,
           head_yaw=yaw+c(t,[(0,0),(3.3,0),(3.7,15),(5.1,0)]),
           hands=grips,hand_dirs=[(0,0,-1)]*2,hand_weights=[weight]*2)
    r.samples[-1]["prop_center"] = list(center)
    r.samples[-1]["grip_targets"] = [list(p) for p in grips]
    r.samples[-1]["grip_weight"] = weight

r.finish("WideCrateTransfer", "Raw input; 8 kg wide crate. Palm contacts 1.95–6.75 s; "
         "three support-adjustment steps turn left; crate rests on 0.45 m table at 6.35 s "
         "before release. No finger bones. Independent transfer first draft.")
