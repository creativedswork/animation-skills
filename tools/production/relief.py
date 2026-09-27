"""Independent attention-and-release performance, with no source clips."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve as c

r = Rig("relief-transfer")
for frame in range(1, r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t = (frame-1)/30
    head = c(t,[(0,43),(.6,45),(1.7,45),(2.08,42),(2.35,39),(3.6,37),
                (4.15,37),(5.35,0),(6,0)])
    chest = c(t,[(0,19),(1.8,20),(2.35,19),(3.3,10),(4.25,10),(5.55,0)])
    lean = c(t,[(0,-3),(1.3,-2),(2.1,-3),(2.8,7),(3.55,4),(4.2,3),(6,2)])
    height = c(t,[(0,.80),(1.4,.803),(2.1,.803),(3.0,.775),(3.9,.791),(6,.793)])
    arm = c(t,[(0,.15),(1.9,.17),(2.5,.12),(3.5,.04),(6,.04)])
    bend = c(t,[(0,1.0),(2.15,1.02),(3.3,.18),(4.1,.1),(6,.1)])
    r.pose((c(t,[(0,.022),(2.2,.022),(3.5,0),(6,0)]),-.035,height),lean,
           [(-.13,0,.13146),(.13,-.08,.13146)], yaw=4, foot_yaws=[0,0],
           chest_yaw=chest,head_yaw=head,
           head_pitch=c(t,[(0,-3),(2.1,-3),(2.65,12),(3.5,5),(5.4,0)]),
           arm_forward=[arm,arm*.6],arm_bend=[bend,bend*.72])
r.finish("ReliefAfterChecking", "Raw input. Attention left-front through 2 s; head confirmation "
         "precedes chest exhale, followed by arm release; attention returns forward at 4.15–5.55 s. "
         "No eye or facial bones. Planted world-space ankles. Independent transfer first draft.")
