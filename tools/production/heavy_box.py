"""20 kg box: load preparation, leg drive, side steps, and supported release."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rig import Rig,curve as c,step
from mathutils import Vector

r=Rig("lift-heavy-box")
prop,table=r.case["scene"]["props"]
box=r.cube("box",prop["center"],prop["dimensions"],(.23,.115,.045,1))
r.table(table)
for x in (-.28,.28):
    r.cube("Box rail",(x,0,.10),(.025,.28,.04),(.11,.055,.025,1),box)
for frame in range(1,r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t=(frame-1)/30
    px=c(t,[(0,0),(4,0),(4.65,.17),(5.15,.32),(5.6,.49),(6.1,.66),(8,.66)])
    pz=c(t,[(0,.8),(.4,.79),(1.4,.34),(1.9,.34),(2.35,.31),(2.65,.34),
             (3.8,.76),(6.1,.76),(6.65,.72),(7.3,.74),(8,.80)])
    lean=c(t,[(0,3),(1.4,61),(1.9,61),(2.35,64),(2.65,61),(3.8,13),
               (6.1,13),(6.65,20),(7.15,20),(8,2)])
    center=Vector((c(t,[(0,0),(4,0),(4.65,.18),(5.15,.39),(5.6,.6),(6.1,.87),(8,.87)]),
                   c(t,[(0,.5),(2.4,.5),(3.8,.42),(6.1,.5),(8,.5)]),
                   c(t,[(0,.2),(2.45,.2),(2.8,.38),(3.8,1.05),(6.1,1.05),
                         (6.65,.95),(8,.95)])))
    box.location=center
    box.keyframe_insert("location")
    left=step(t,4.72,5.14,(-.14,-.06,.13146),(.23,-.06,.13146),.045)
    left=step(t,5.73,6.12,left,(.54,-.06,.13146),.04)
    right=step(t,4.18,4.65,(.14,0,.13146),(.45,0,.13146),.045)
    right=step(t,5.2,5.65,right,(.80,0,.13146),.04)
    grips=[center+Vector((x,0,.10)) for x in (-.28,.28)]
    weight=c(t,[(0,0),(1.4,0),(1.9,1),(7,1),(7.5,0),(8,0)])
    r.pose((px,c(t,[(0,-.04),(3.8,-.02),(5,.04),(6.1,.07),(8,.07)]),pz),lean,[left,right],hands=grips,
           hand_dirs=[(0,0,-1)]*2,hand_weights=[weight]*2,
           head_yaw=c(t,[(0,0),(3.8,0),(4.25,-24),(5.9,-17),(6.7,0)]))
    r.samples[-1].update(prop_center=list(center),grip_targets=[list(p) for p in grips],grip_weight=weight)
r.finish("HeavyBoxLift", "Raw input. 20 kg box held after 1.9 s, loading pause through 2.45 s, "
         "leg/hip drive and four small lateral steps. Box bottom rests on 0.75 m table at 6.65 s; "
         "release begins after 7 s. Palm-only grasp, no finger rig or rigid-body simulation.")
