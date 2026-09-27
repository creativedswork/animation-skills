"""A right-rear stimulus, orienting pause, and three support changes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rig import Rig,curve as c,step

r=Rig("alert-turn")
for frame in range(1,r.scene.frame_end+1):
    r.scene.frame_set(frame)
    t=(frame-1)/30
    yaw=c(t,[(0,0),(1.6,0),(2.12,-44),(2.7,-91),(3.3,-133),(5,-133)])
    head=c(t,[(0,0),(1.08,0),(1.36,-62),(1.65,-62),(2.5,-123),(3.2,-133),(5,-133)])
    chest=c(t,[(0,0),(1.2,0),(1.57,-24),(1.78,-24),(2.55,-102),(3.25,-133)])
    left=step(t,2.18,2.7,(-.13,0,.13146),(.14,.10,.13146))
    right=step(t,1.72,2.15,(.13,0,.13146),(.26,-.15,.13146))
    right=step(t,2.76,3.30,right,(.32,-.10,.13146))
    r.pose((c(t,[(0,0),(1.6,-.025),(2.15,.09),(2.7,.18),(3.3,.23)]),
            c(t,[(0,0),(1.6,-.035),(3.3,0)]),
            c(t,[(0,.81),(1,.81),(1.3,.775),(1.65,.77),(2.8,.76),(3.5,.79)])),
           c(t,[(0,2),(1.1,2),(1.4,-3),(2.3,5),(3.4,2)]),[left,right],
           yaw=yaw,foot_yaws=[c(t,[(0,0),(2.18,0),(2.7,-132)]),
                              c(t,[(0,0),(1.72,0),(2.15,-62),(2.76,-62),(3.3,-132)])],
           chest_yaw=chest,head_yaw=head,head_pitch=-2,
           arm_forward=[c(t,[(0,.05),(1.1,.05),(1.45,.32),(3.4,.2)]),
                        c(t,[(0,.05),(1.15,.05),(1.6,.22),(3.4,.1)])],
           arm_bend=c(t,[(0,.15),(1.1,.15),(1.6,.8),(3.4,.55)]))
r.finish("AlertTurn", "Stimulus at 1 s; head begins after 1.08 s, torso judges then turns on "
         "three support changes. Final heading approximately -133 degrees toward (2,-2,1.5). "
         "No facial or eye animation, no source keys.")
