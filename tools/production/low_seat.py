"""Independently authored from the raw rig and the low-seat task definition."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rig import Rig, curve


rig = Rig("low-seat-transfer", "corrected")
for frame in range(rig.scene.frame_start, rig.scene.frame_end + 1):
    rig.scene.frame_set(frame)
    t = (frame - 1) / 30
    x = curve(t, [(0, 0), (2.7, 0), (3.3, .068), (3.7, .065), (4.5, -.018), (6, -.018)])
    y = curve(t, [(0, 0), (.5, 0), (1.3, .07), (1.85, .235), (2.65, .335),
                  (3.25, .345), (4.15, .49), (4.7, .525), (6, .525)])
    z = curve(t, [(0, .365), (.5, .365), (1.1, .364), (1.35, .395), (1.85, .61),
                  (2.65, .823), (2.95, .813), (3.35, .813), (3.8, .812),
                  (4.2, .78), (4.65, .79), (6, .79)])
    lean = curve(t, [(0, 7), (.5, 7), (1.25, 43), (1.55, 40), (2.1, 25),
                     (2.7, 3), (3.2, 5), (3.9, 7), (4.6, 2), (6, 2)])
    foot_y = curve(t, [(0, .34), (3.25, .34), (3.6, .43), (3.95, .67), (4.2, .76), (6, .76)])
    foot_z = curve(t, [(0, .131), (3.25, .131), (3.6, .225), (3.92, .18), (4.2, .131), (6, .131)])
    arms = curve(t, [(0, .23), (.6, .23), (1.35, .8), (2, .6), (2.8, .1),
                     (3.7, .16), (4.6, .12), (6, .12)])
    rig.pose((x, y, z), lean, [(-.125, foot_y, foot_z), (.125, .34, .131)],
             arm_forward=arms, arm_bend=.12)

rig.finish("LowSeatRiseStep", "从原始 GLB 独立制作；未读取其他 case 的作品、评价或关键帧。"
           "双脚初始横向间距 0.25 m、前向 0.34 m；右脚承重，左脚于 3.25–4.2 秒迈出。"
           "程序生成的逐帧 FK 关键帧，腿部用定长两段求解；无源动作复用。")
