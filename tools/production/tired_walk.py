"""Short, low-clearance steps followed by recovery and renewed attention."""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve as c, step

r=Rig("tired-walk")
events=[]
for i in range(9):
    side=i%2
    events.append((side,.25+i*.43,.64+i*.43,
                   ((-.12 if side==0 else .12),min(2,.24*(i+1)),.13146)))
events.append((1,4.15,4.55,(.12,2,.13146)))
for frame in range(1,r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t=(frame-1)/30
    feet=[(-.12,0,.13146),(.12,0,.13146)]
    sway=bob=0
    for side,a,b,end in events:
        feet[side]=step(t,a,b,feet[side],end,.04)
        if a<t<b:
            u=(t-a)/(b-a)
            sway=(.018 if side==0 else -.018)*math.sin(math.pi*u)
            bob=.007*math.sin(math.pi*u)**2
    y=c(t,[(0,0),(.3,.02),(.7,.20),(1.2,.47),(2,.92),(3,1.48),(3.9,1.88),(4.55,2),(7,2)])
    lean=c(t,[(0,13),(.6,16),(3.7,16),(4.6,25),(5.2,20),(5.7,24),(6.3,15),(7,9)])
    height=c(t,[(0,.80),(.5,.782),(4,.782),(4.65,.785),(5.2,.80),(5.7,.793),(6.5,.81),(7,.81)])
    swing=.16*math.sin((t-.25)*math.pi/.43)*c(t,[(0,0),(.5,1),(3.8,1),(4.6,0)])
    r.pose((sway,y,height+bob),lean,feet,arm_forward=[swing+.12,-swing+.10],arm_bend=.18,
           head_pitch=c(t,[(0,18),(3.9,20),(4.65,31),(5.7,28),(6.35,-2),(7,-2)]))
    r.samples[-1]["support"]=[s for s in (0,1) if not any(e[0]==s and e[1]<t<e[2] for e in events)]
r.finish("TiredWalkRecover", "Raw rig. 2 m in short low-clearance steps; halt by 4.55 s; "
         "two uneven chest recovery motions and head lifted ahead of the torso at 6.35 s. "
         "No source animation, face or eye controls.")
