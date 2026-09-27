"""A non-looping 3 m walk with authored world-space footfalls."""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve as c, step, turn
from mathutils import Vector

r = Rig("walk-turn-stop")
events = [
    (0,.28,.72,(-.12,.32,.13146),0), (1,.74,1.12,(.12,.65,.13146),0),
    (0,1.14,1.52,(-.12,.98,.13146),0), (1,1.54,1.92,(.12,1.31,.13146),0),
    (0,1.94,2.32,(-.12,1.64,.13146),0), (1,2.34,2.72,(.12,1.96,.13146),0),
    (0,2.78,3.18,(-.12,2.13,.13146),-15),
    (1,3.22,3.66,(.30,2.15,.13146),-60),
    (0,3.70,4.12,(.47,1.87,.13146),-90),
    (1,4.16,4.58,(.75,2.13,.13146),-90),
    (0,4.64,5.08,(1,1.87,.13146),-90),
    (1,5.14,5.60,(1,2.13,.13146),-90),
]
for frame in range(1,r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t=(frame-1)/30
    feet=[(-.12,0,.13146),(.12,0,.13146)]
    angles=[0,0]
    sway=bob=0
    for side,a,b,end,angle in events:
        feet[side]=step(t,a,b,feet[side],end)
        angles[side]=c(t,[(a,angles[side]),(b,angle)])
        if a<t<b:
            u=(t-a)/(b-a)
            sway=(.022 if side==0 else -.022)*math.sin(math.pi*u)
            bob=.012*math.sin(math.pi*u)**2
    y=c(t,[(0,0),(.35,.04),(.75,.27),(1.15,.61),(1.55,.94),(1.95,1.27),
           (2.35,1.60),(2.75,1.86),(3.3,2),(6,2)])
    x=c(t,[(0,0),(3.15,0),(3.66,.23),(4.12,.46),(4.58,.70),(5.08,.91),(5.6,1),(6,1)])
    yaw=c(t,[(0,0),(2.95,0),(3.65,-52),(4.12,-90),(6,-90)])
    envelope=c(t,[(0,0),(.4,1),(4.7,1),(5.6,0)])
    swing=.45*math.sin((t-.3)*math.pi/.4)*envelope
    pelvis=Vector((x+sway*math.cos(math.radians(yaw)),y+sway*math.sin(math.radians(yaw)),.81))
    # Keep the pelvis high at passing, lowering only when the two contacts require it.
    leg_length=sum(r.arm.data.bones[n+".L"].length for n in ("Thigh","Shin"))*r.scale-.008
    for i,foot in enumerate(feet):
        hip_xy=pelvis+turn(((-.105 if i==0 else .105)*r.scale,0,0),yaw)
        horizontal=(hip_xy.x-foot[0])**2+(hip_xy.y-foot[1])**2
        pelvis.z=min(pelvis.z,foot[2]+math.sqrt(leg_length**2-horizontal)-.03*r.scale)
    r.pose(pelvis,
           c(t,[(0,1),(.5,5),(4.9,5),(5.45,9),(5.9,1)]),feet,
           yaw=yaw,foot_yaws=angles,head_yaw=c(t,[(0,0),(2.8,0),(3.45,-65),(4,-90)]),
           arm_forward=[swing,-swing],arm_bend=.28)
    r.samples[-1]["support"]=[s for s in (0,1) if not any(e[0]==s and e[1]<t<e[2] for e in events)]
r.finish("WalkTurnStop", "New 6 s clip; 2 m forward, right 90 degrees, 1 m and stop. "
         "Twelve authored swings with world-space stance positions, independent root trajectory. "
         "No input animation keys. Foot bones stay flat because no toe chain is present.")
