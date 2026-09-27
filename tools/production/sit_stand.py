"""Authored bench sit/hold/rise; no input animation keys are reused."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve


rig = Rig("sit-stand")
for frame in range(rig.scene.frame_start, rig.scene.frame_end + 1):
    rig.scene.frame_set(frame)
    t = (frame - 1) / 30
    y = curve(t, [(0, 0), (.5, 0), (1.1, -.055), (1.75, -.20), (2.35, -.30),
                  (3.8, -.30), (4.5, -.24), (5.05, -.11), (5.7, .006), (6.15, 0), (7, 0)])
    z = curve(t, [(0, .833), (.5, .833), (1.2, .775), (1.85, .595), (2.35, .528),
                  (2.6, .525), (3.8, .525), (4.4, .522), (4.65, .55),
                  (5.15, .705), (5.75, .837), (6.2, .833), (7, .833)])
    lean = curve(t, [(0, 2), (.5, 2), (1.25, 31), (1.8, 34), (2.6, 8),
                     (3.8, 8), (4.5, 39), (4.85, 35), (5.25, 23), (5.9, 1),
                     (6.3, 2), (7, 2)])
    arms = curve(t, [(0, .12), (.5, .12), (1.35, .65), (2.6, .25),
                     (3.8, .25), (4.55, .7), (5.1, .5), (6, .12), (7, .12)])
    rig.pose((0, y, z), lean, [(-.125, .05, .131), (.125, .05, .131)],
             arm_forward=arms, arm_bend=.1)

rig.finish("SitStand", "从固定原始 GLB 制作，清除原始动作；双脚保持 0.25 m 间距、前向 0.05 m。"
           "0.5–2.6 秒坐下，2.6–3.8 秒稳定坐住，随后前倾、离座、起立，6.3 秒后站稳。"
           "木凳座面 0.48 m，手臂仅做平衡动作，没有手部支撑。")
