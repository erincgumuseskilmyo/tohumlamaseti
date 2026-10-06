"""Slim glass liquid thermometer with steel base sleeve and hanging ring. ~17 cm, standing on its
sleeve, origin at the sleeve's base. Run: python models/thermometer_gen.py models"""
import math, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lowpoly_lib import *

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
R_GLASS = 0.0045
SLEEVE_TOP, TUBE_TOP = 0.042, 0.152
parts = {}

# --- steel protective sleeve at the base (chamfered cylinder, 3 vent slots, blue grip ring)
sleeve = [(0.0065, 0.0), (0.0080, 0.0015), (0.0080, SLEEVE_TOP - 0.004), (0.0060, SLEEVE_TOP)]
parts["sleeve"] = mesh(*lathe(sleeve, n=12, cap_bottom=True, cap_top=False), "steel_brushed")
parts["sleeve_ring"] = mesh(*lathe([(0.0086, 0.010), (0.0086, 0.016)], n=12, cap_bottom=False, cap_top=False), "steel_blue")
for i in range(3):  # vent slots: dark quads on the sleeve surface
    a = 2*math.pi*i/3 + math.pi/6
    n = np.array([math.cos(a), 0, math.sin(a)]); t = np.array([-math.sin(a), 0, math.cos(a)])
    c = n * 0.0082
    q = np.array([c - t*0.0015 + [0, 0.022, 0], c + t*0.0015 + [0, 0.022, 0], c + t*0.0015 + [0, 0.034, 0], c - t*0.0015 + [0, 0.034, 0]])
    parts[f"slot_{i}"] = mesh(q, np.array([(0, 2, 1), (0, 3, 2)]), "steel_blue")
# amber "37" set-point band on the sleeve top
parts["setpoint"] = mesh(*lathe([(0.0084, SLEEVE_TOP - 0.0055), (0.0084, SLEEVE_TOP - 0.0015)], n=12, cap_bottom=False, cap_top=False), "amber")

# --- inside the glass: white scale card, tick marks, red column + bulb
CARD_Z = 0.0018                                   # card sits just behind the column (towards +Z)
card = np.array([(-0.0026, SLEEVE_TOP - 0.006, CARD_Z), (0.0026, SLEEVE_TOP - 0.006, CARD_Z), (0.0026, TUBE_TOP - 0.006, CARD_Z), (-0.0026, TUBE_TOP - 0.006, CARD_Z)])
parts["scale_card"] = mesh(card, np.array([(0, 2, 1), (0, 3, 2)]), "white_plastic")   # faces -Z (front)
ticks = []
for k in range(11):                                # major ticks every 10 units, minor between
    y = SLEEVE_TOP + 0.004 + k * 0.0098
    w = 0.0026 if k % 2 == 0 else 0.0016
    ticks.append(np.array([(-0.0026, y, CARD_Z - 0.0002), (-0.0026 + w, y, CARD_Z - 0.0002), (-0.0026 + w, y + 0.0012, CARD_Z - 0.0002), (-0.0026, y + 0.0012, CARD_Z - 0.0002)]))
TV = np.vstack(ticks); TF = np.vstack([np.array([(0, 2, 1), (0, 3, 2)]) + 4*i for i in range(len(ticks))])
parts["ticks"] = mesh(TV, TF, "steel_blue")
# amber marker tick at body temperature (37 °C)
ym = SLEEVE_TOP + 0.004 + 6.6 * 0.0098
parts["tick_37"] = mesh(np.array([(-0.0026, ym, CARD_Z - 0.0003), (0.0026, ym, CARD_Z - 0.0003), (0.0026, ym + 0.0016, CARD_Z - 0.0003), (-0.0026, ym + 0.0016, CARD_Z - 0.0003)]),
                        np.array([(0, 2, 1), (0, 3, 2)]), "amber")
parts["bulb"] = mesh(*lathe([(0.0015, 0.018), (0.0032, 0.021), (0.0032, 0.030), (0.0014, 0.034)], n=8, cap_bottom=True, cap_top=False), "mercury_red")
parts["column"] = mesh(*lathe([(0.0013, 0.033), (0.0013, ym + 0.0006)], n=6, cap_bottom=False, cap_top=True), "mercury_red")
parts["capillary"] = mesh(*lathe([(0.0013, ym + 0.0006), (0.0013, TUBE_TOP - 0.008)], n=6, cap_bottom=False, cap_top=True), "white_plastic")

# --- glass tube (translucent, rounded top) from inside the sleeve to the cap
tube = [(R_GLASS, SLEEVE_TOP - 0.004), (R_GLASS, TUBE_TOP - 0.004), (R_GLASS * 0.7, TUBE_TOP - 0.001), (0.0008, TUBE_TOP)]
parts["glass"] = mesh(*lathe(tube, n=12, cap_bottom=False, cap_top=True), "glass")

# --- steel top cap + hanging ring (low-poly torus in the XY plane)
parts["cap"] = mesh(*lathe([(0.0050, TUBE_TOP - 0.002), (0.0058, TUBE_TOP), (0.0058, TUBE_TOP + 0.007), (0.0030, TUBE_TOP + 0.010)], n=12, cap_bottom=False, cap_top=True), "steel_brushed")
RING_R, RING_T, RING_Y = 0.0075, 0.0016, TUBE_TOP + 0.010 + 0.0075
V, F = [], []
NS, NT = 10, 4
for i in range(NS):
    a = 2*math.pi*i/NS
    c = np.array([RING_R*math.cos(a), RING_Y + RING_R*math.sin(a), 0]); rad = np.array([math.cos(a), math.sin(a), 0])
    for j in range(NT):
        b = 2*math.pi*j/NT + math.pi/4
        V.append(c + RING_T*(math.cos(b)*rad + math.sin(b)*np.array([0, 0, 1])))
for i in range(NS):
    for j in range(NT):
        a0, a1 = i*NT + j, i*NT + (j+1) % NT
        b0, b1 = ((i+1) % NS)*NT + j, ((i+1) % NS)*NT + (j+1) % NT
        F.append((a0, b0, b1)); F.append((a0, b1, a1))
parts["ring"] = mesh(np.array(V), np.array(F), "steel_brushed")

tris, bounds = export(parts, OUT, "thermometer")
print("triangles:", tris, "bounds:", bounds.round(4).tolist(), "bad:", check(parts))
render(parts, os.path.join(OUT, "thermometer_onizleme.png"), yaw_deg=200, pitch_deg=12, zoom=2.3)
print("done")
