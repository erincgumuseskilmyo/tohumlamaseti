"""Portable semen-straw thaw cup: blue cylinder on a rectangular foot, flat back spine,
hinged black lid with thermometer disc (open). ~20 cm tall, origin at centre of base.
Run: python models/strawthawer_gen.py models"""
import math, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lowpoly_lib import *

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
R_BODY, TOP = 0.052, 0.185           # cup radius / rim height
HINGE = np.array([0.0, TOP + 0.012, 0.062])  # hinge axis (along X) at top of the back spine
LID_ANGLE = math.radians(100)        # open angle
parts = {}

# --- foot: chamfered rectangular base, slightly wider at the bottom
foot = [rect8(0.078, 0.066, 0.016, 0.0), rect8(0.080, 0.068, 0.016, 0.006), rect8(0.080, 0.068, 0.016, 0.030),
        rect8(0.072, 0.062, 0.014, 0.040)]
parts["foot"] = mesh(*loft(foot, cap_bottom=True, cap_top=True), "steel_blue_lt")
# --- cup body: cylinder with flared collar at the base and a thicker rim on top
body = [(0.062, 0.040), (0.056, 0.055), (R_BODY, 0.075), (R_BODY, TOP - 0.010), (R_BODY + 0.004, TOP - 0.004), (R_BODY + 0.004, TOP)]
parts["body"] = mesh(*lathe(body, n=16, cap_bottom=False, cap_top=False), "steel_blue_lt")
# rim ring + inner liner + water
parts["rim"] = mesh(*band(ring(R_BODY + 0.004, TOP, 16), ring(R_BODY - 0.006, TOP, 16)), "steel_blue")
V, F = lathe([(R_BODY - 0.006, TOP), (R_BODY - 0.006, 0.090), (R_BODY - 0.012, 0.084)], n=16, cap_bottom=False, cap_top=True)
parts["liner"] = mesh(V, F[:, ::-1], "steel_blue")
parts["water"] = mesh(*lathe([(R_BODY - 0.0065, 0.160)], n=16, cap_bottom=False, cap_top=True), "frost_cyan")
# --- flat back spine: box from the foot up past the rim, carries the hinge
spine = [rect8(0.030, 0.014, 0.004, 0.040, cz=0.058), rect8(0.030, 0.014, 0.004, TOP + 0.006, cz=0.058),
         rect8(0.024, 0.010, 0.003, TOP + 0.014, cz=0.058)]
parts["spine"] = mesh(*loft(spine, cap_bottom=False, cap_top=True), "steel_blue_lt")
# hinge barrel (black) along X
V, F = lathe([(0.008, -0.022), (0.008, 0.022)], n=8)
parts["hinge"] = mesh(V @ rot_y_to("x").T + HINGE, F, "rubber_black")
# --- front label (amber) + white text plate + small green indicator on the foot
FZ = -0.068 - 0.0015
def front_plate(cx, cy, hw, hh, depth, mat):
    r = [(cx-hw, cy-hh), (cx+hw, cy-hh), (cx+hw, cy+hh), (cx-hw, cy+hh)]
    V, F = loft([[(x, y, FZ) for x, y in r], [(x, y, FZ-depth) for x, y in r]], cap_bottom=False, cap_top=True)
    return mesh(V, F, mat)
parts["label"] = front_plate(0.030, 0.018, 0.026, 0.008, 0.002, "amber")
parts["label_txt"] = front_plate(0.030, 0.018, 0.016, 0.003, 0.0035, "white_plastic")
V, F = lathe([(0.005, 0.0), (0.005, 0.004)], n=8, cap_bottom=False, cap_top=True)
parts["led"] = mesh(V @ rot_y_to("-z").T + np.array([-0.040, 0.018, FZ]), F, "led_green")

# --- lid assembly, built closed (flat over the cup) then rotated open about the hinge
lid = {}
disc = [(0.040, 0.0), (0.048, 0.004), (0.048, 0.010), (0.044, 0.012)]
lid["lid_disc"] = lathe(disc, n=16, cap_bottom=True, cap_top=True)
lid["lid_dial"] = lathe([(0.030, 0.012), (0.030, 0.014)], n=12, cap_bottom=False, cap_top=True)           # white thermometer face
lid["lid_needle"] = (np.array([(-0.0015, 0.0145, 0.004), (0.0015, 0.0145, 0.004), (0.0015, 0.0145, -0.024), (-0.0015, 0.0145, -0.024)]),
                     np.array([(0, 1, 2), (0, 2, 3)]))
lid["lid_pivot"] = lathe([(0.004, 0.012), (0.004, 0.016)], n=8, cap_bottom=False, cap_top=True)
# underside: steel centre boss + dark recess ring (what you see when the lid is open)
lid["lid_boss"] = lathe([(0.012, -0.004), (0.012, 0.0)], n=12, cap_bottom=True, cap_top=False)
lid["lid_ring"] = lathe([(0.026, -0.002), (0.026, 0.0)], n=16, cap_bottom=True, cap_top=False)
# arm from the disc back to the hinge + lever tab beyond the hinge
arm_z0, arm_z1 = 0.030, HINGE[2] + 0.030
lid["lid_arm"] = loft([rect8(0.012, (arm_z1-arm_z0)/2, 0.002, 0.004, cz=(arm_z0+arm_z1)/2), rect8(0.012, (arm_z1-arm_z0)/2, 0.002, 0.014, cz=(arm_z0+arm_z1)/2)])
lid["lid_tab"] = loft([rect8(0.010, 0.006, 0.002, 0.014, cz=HINGE[2] + 0.024), rect8(0.010, 0.006, 0.002, 0.034, cz=HINGE[2] + 0.024)])
# lid local origin = cup axis at rim height; rotate about hinge axis (X) by LID_ANGLE
ca, sa = math.cos(LID_ANGLE), math.sin(LID_ANGLE)
Rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
def place(V):
    Vw = V + np.array([0, TOP + 0.012, 0])            # closed pose, sitting on the rim
    return (Vw - HINGE) @ Rx.T + HINGE
mats = {"lid_disc": "rubber_black", "lid_dial": "white_plastic", "lid_needle": "rubber_black", "lid_pivot": "amber",
        "lid_arm": "rubber_black", "lid_tab": "rubber_black", "lid_boss": "steel_brushed", "lid_ring": "steel_blue"}
for k, (V, F) in lid.items():
    parts[k] = mesh(place(np.asarray(V, float)), F, mats[k])

tris, bounds = export(parts, OUT, "strawthawer")
print("triangles:", tris, "bounds:", bounds.round(3).tolist(), "bad:", check(parts))
render(parts, os.path.join(OUT, "strawthawer_onizleme.png"), yaw_deg=210, pitch_deg=22, zoom=2.4)
print("done")
