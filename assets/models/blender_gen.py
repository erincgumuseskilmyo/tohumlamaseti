"""Suni Tohumlama Alet Avi -- tum oyun nesnelerinin low-poly 3D modelleri.

Blender headless ile calistirilir:
    blender --background --python blender_gen.py -- [model-adi ...]

Argumansiz calistirinca MODELS sozlugundeki tum modeller uretilir ve her biri
bu klasore <ad>.glb olarak yazilir. Oyun modelleri bounding-box'a gore
olceklediginden mutlak boyut degil, oranlar onemlidir.

Konvansiyon: Blender Z-up insa edilir, nesnenin "on" yuzu -Y'ye bakar
(glTF export'undaki Z-up -> Y-up donusumu ile oyun kamerasina donuk gelir).
"""
import bpy, math, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Oyunun buz/frost paleti (CSS degiskenleriyle ayni ailede) ---------------
PALETTE = {
    "steel":       ("#b9c4cb", 0.90, 0.35),
    "steel_dark":  ("#6f7d86", 0.85, 0.45),
    "blue_dark":   ("#1c3947", 0.15, 0.65),
    "blue_mid":    ("#2f5b6f", 0.20, 0.60),
    "frost":       ("#8ed6f2", 0.00, 0.35),
    # Not: cok acik bir ton (eski #cfe9f5) acik temali sahnede kayboluyordu
    "frost_pale":  ("#a8cfe2", 0.00, 0.30),
    "white":       ("#eef3f5", 0.00, 0.50),
    "paper":       ("#f7f9fa", 0.00, 0.85),
    "rubber":      ("#15181b", 0.00, 0.90),
    "amber":       ("#ffd166", 0.00, 0.55),
    "red":         ("#ef5b60", 0.00, 0.55),
    "green":       ("#7fe0a7", 0.00, 0.55),
    "wood":        ("#b98a52", 0.00, 0.75),
    "wood_dark":   ("#7a5a33", 0.00, 0.80),
    "skin":        ("#e8d5c4", 0.00, 0.60),
    # Tamami metal olan modeller icin: ortam yansimasi olmayan sahnede metallic 0.9
    # neredeyse siyaha duser, bu yuzden parlak krom daha dusuk metallic ile taklit edilir.
    "chrome":      ("#dbe3e8", 0.30, 0.22),
    "chrome_dark": ("#9fb0ba", 0.30, 0.30),
    "plastic_blue":   ("#1f7ad4", 0.00, 0.42),
    "plastic_blue_d": ("#15599f", 0.00, 0.48),
}
_mats = {}


def hex2rgb(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # sRGB -> linear
    return (f(r), f(g), f(b), 1.0)


def mat(name):
    if name in _mats:
        return _mats[name]
    hexcol, metallic, rough = PALETTE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex2rgb(hexcol)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    _mats[name] = m
    return m


# --- Primitif yardimcilari --------------------------------------------------
def _finish(ob, m, smooth):
    ob.data.materials.append(mat(m))
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def cyl(r=0.05, h=0.2, loc=(0, 0, 0), rot=(0, 0, 0), v=12, m="steel", smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=h, location=loc, rotation=rot)
    return _finish(bpy.context.object, m, smooth)


def cone(r1=0.05, r2=0.0, h=0.2, loc=(0, 0, 0), rot=(0, 0, 0), v=12, m="steel", smooth=True):
    bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=r2, depth=h, location=loc, rotation=rot)
    return _finish(bpy.context.object, m, smooth)


def box(size=(0.1, 0.1, 0.1), loc=(0, 0, 0), rot=(0, 0, 0), m="steel"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = size
    return _finish(ob, m, False)


def ball(r=0.05, loc=(0, 0, 0), m="steel", seg=14, ring_count=8, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=ring_count, radius=r, location=loc)
    ob = bpy.context.object
    ob.scale = scale
    return _finish(ob, m, True)


def ring(R=0.06, r=0.01, loc=(0, 0, 0), rot=(0, 0, 0), m="steel", mseg=18, nseg=7):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=mseg,
                                     minor_segments=nseg, location=loc, rotation=rot)
    return _finish(bpy.context.object, m, True)


RX = math.radians


def arc(cx, cz, R, a0, a1, n=6, r=0.008, y=0.0, m="steel", ball_ends=False, bs=None):
    """XZ duzleminde (cx, cz) merkezli yayi n silindirle kurar; eklemlere kure koyar.
    Aci dereceyle verilir. Silindir varsayilan ekseni Z oldugundan yonu (cos a, sin a)
    yapmak icin Y ekseninde (pi/2 - a) kadar dondurulur."""
    pts = []
    for i in range(n + 1):
        t = RX(a0 + (a1 - a0) * i / n)
        pts.append((cx + R * math.cos(t), cz + R * math.sin(t)))
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        dx, dz = x1 - x0, z1 - z0
        seg = math.hypot(dx, dz)
        ang = math.atan2(dz, dx)
        cyl(r, seg * 1.25, ((x0 + x1) / 2, y, (z0 + z1) / 2),
            rot=(0, math.pi / 2 - ang, 0), v=8, m=m)
    for x, z in pts[1:-1]:
        ball(r, (x, y, z), m=m, seg=8, ring_count=5)
    if ball_ends:
        ball(bs or r * 1.9, (pts[-1][0], y, pts[-1][1]), m=m, seg=12, ring_count=8)
    return pts


# --- Modeller ---------------------------------------------------------------
def thermometer():
    cyl(0.006, 0.34, (0, 0, 0.02), v=10, m="frost_pale")            # cam govde
    cyl(0.0022, 0.30, (0, -0.004, 0.01), v=6, m="red")              # kirmizi sutun
    ball(0.011, (0, 0, -0.16), m="red")                             # hazne
    cyl(0.0075, 0.02, (0, 0, 0.20), v=10, m="steel")                # ust kapak
    ring(0.009, 0.0025, (0, 0, 0.205), m="steel")
    box((0.013, 0.001, 0.14), (0, -0.0065, 0.03), m="white")        # skala serisi


def kit_case():
    box((0.34, 0.14, 0.24), (0, 0, 0), m="blue_dark")               # govde
    box((0.345, 0.145, 0.018), (0, 0, 0.055), m="blue_mid")         # kapak ayrim cizgisi
    box((0.06, 0.02, 0.03), (-0.08, -0.072, 0.045), m="steel")      # kilitler
    box((0.06, 0.02, 0.03), (0.08, -0.072, 0.045), m="steel")
    box((0.26, 0.09, 0.05), (0, 0, 0.128), m="blue_dark")           # sap tabani
    ring(0.055, 0.012, (0, 0, 0.135), rot=(RX(90), 0, 0), m="rubber", mseg=16)   # sap
    box((0.30, 0.005, 0.05), (0, -0.071, -0.04), m="frost")         # on serit


def ai_gun():
    # Gercek pistole ~90:1 inceliktedir; oyun en uzun kenari sabitledigi icin
    # okunabilirlik adina en-boy orani ~9:1'e abartildi.
    cyl(0.020, 0.36, (0, 0, 0), rot=(RX(90), 0, 0), v=12, m="steel")            # celik govde
    cyl(0.013, 0.09, (0, 0.215, 0), rot=(RX(90), 0, 0), v=10, m="steel_dark")   # piston mili
    ring(0.038, 0.011, (0, 0.265, 0), rot=(0, RX(90), 0), m="steel_dark")       # arka basparmak halkasi
    cyl(0.027, 0.06, (0, 0.10, 0), rot=(RX(90), 0, 0), v=12, m="blue_mid")      # tutus bandi
    cyl(0.024, 0.016, (0, 0.02, 0), rot=(RX(90), 0, 0), v=12, m="amber")        # kilit bilezigi
    cone(0.020, 0.010, 0.05, (0, -0.205, 0), rot=(RX(90), 0, 0), v=12, m="steel")   # uc

def sheath():
    cyl(0.015, 0.36, (0, 0, 0), rot=(RX(90), 0, 0), v=12, m="frost_pale")       # seffaf kilif
    cyl(0.026, 0.05, (0, 0.175, 0), rot=(RX(90), 0, 0), v=12, m="white")        # arka bilezik
    ring(0.028, 0.007, (0, 0.155, 0), rot=(0, RX(90), 0), m="frost")            # tutma flansi
    cyl(0.017, 0.02, (0, -0.10, 0), rot=(RX(90), 0, 0), v=12, m="frost")        # orta isaret bandi
    cone(0.015, 0.008, 0.04, (0, -0.20, 0), rot=(RX(90), 0, 0), v=12, m="frost_pale")   # acik uc

def straw_forceps():
    for s in (-1, 1):
        box((0.012, 0.30, 0.004), (s * 0.016, 0.02, 0), rot=(0, 0, RX(s * 3.2)), m="steel")     # kollar
        ring(0.028, 0.006, (s * 0.030, 0.185, 0), rot=(RX(90), 0, 0), m="steel_dark")           # halka saplar
        box((0.010, 0.10, 0.004), (s * 0.010, -0.19, 0), rot=(0, 0, RX(-s * 2.4)), m="steel")   # cene
    cyl(0.010, 0.014, (0, -0.02, 0), rot=(RX(90), 0, 0), v=10, m="steel_dark")  # pim
    box((0.03, 0.02, 0.004), (0, -0.245, 0), m="steel_dark")                    # uc kavrama


def straw_cutter():
    """Gercek urun: mavi, yuvarlak, cevresi tirtikli plastik payet kesici;
    ustunde donen kapak, kucuk payet agzi ve yandan cikan kollu tutamak.
    Disk ekseni Y boyunca kurulur ki oyunda yuzu kameraya donuk gelsin.
    Buyuk diskler duz golgeli (smooth=False) -- yoksa kapak kure gibi okunuyor."""
    AX = (RX(90), 0, 0)
    cyl(0.052, 0.042, (0, 0.012, 0), rot=AX, v=24, m="plastic_blue", smooth=False)   # alt govde
    for i in range(12):                                                              # govde tirtiklari
        a = 2 * math.pi * i / 12
        cyl(0.0040, 0.030, (0.053 * math.cos(a), 0.014, 0.053 * math.sin(a)),
            rot=AX, v=6, m="plastic_blue")
    cyl(0.049, 0.018, (0, -0.018, 0), rot=AX, v=24, m="plastic_blue", smooth=False)  # donen kapak
    for i in range(12):                                                              # kapak tirtiklari
        a = 2 * math.pi * i / 12 + 0.26
        cyl(0.0035, 0.014, (0.050 * math.cos(a), -0.018, 0.050 * math.sin(a)),
            rot=AX, v=6, m="plastic_blue")
    cyl(0.040, 0.0025, (0, -0.0285, 0), rot=AX, v=24, m="plastic_blue_d", smooth=False)  # kapak ici daire
    box((0.042, 0.007, 0.008), (-0.004, -0.031, 0.013), rot=(0, 0, RX(-16)), m="plastic_blue")  # hizalama kaburgasi
    cyl(0.0080, 0.016, (-0.022, -0.034, 0.018), rot=AX, v=10, m="plastic_blue")      # payet agzi
    cyl(0.0038, 0.018, (-0.022, -0.036, 0.018), rot=AX, v=8, m="rubber")             # agiz deligi
    box((0.045, 0.011, 0.009), (0.072, -0.016, -0.006), m="plastic_blue")            # kol
    box((0.011, 0.013, 0.028), (0.098, -0.016, -0.006), m="plastic_blue")            # kol ucu tirnagi


def glove():
    cyl(0.070, 0.30, (0, 0, -0.10), v=14, m="frost_pale")                       # uzun kol
    cyl(0.080, 0.05, (0, 0, -0.245), v=14, m="frost")                           # katlanmis manset
    box((0.155, 0.055, 0.15), (0, 0, 0.115), m="frost_pale")                    # avuc ici
    for i, x in enumerate((-0.054, -0.018, 0.018, 0.054)):                      # 4 parmak
        h = 0.135 - abs(i - 1.5) * 0.018
        cyl(0.019, h, (x, 0, 0.19 + h / 2 - 0.028), v=8, m="frost_pale")
        ball(0.019, (x, 0, 0.19 + h - 0.028), m="frost_pale", seg=10, ring_count=6)
    cyl(0.021, 0.10, (-0.088, 0, 0.115), rot=(0, RX(50), 0), v=8, m="frost_pale")   # basparmak
    ball(0.021, (-0.125, 0, 0.145), m="frost_pale", seg=10, ring_count=6)

def lubricant():
    cone(0.052, 0.045, 0.26, (0, 0, 0), v=16, m="blue_mid")                     # sise govdesi
    cone(0.045, 0.020, 0.06, (0, 0, 0.16), v=16, m="blue_mid")                  # omuz
    cyl(0.016, 0.05, (0, 0, 0.212), v=12, m="white")                            # boyun
    cone(0.018, 0.010, 0.045, (0, 0, 0.255), v=12, m="white")                   # ucu kapak
    cyl(0.053, 0.10, (0, 0, -0.01), v=16, m="frost")                            # etiket bandi


def alcohol():
    cyl(0.050, 0.24, (0, 0, 0), v=16, m="frost_pale")                           # sise
    cone(0.050, 0.020, 0.06, (0, 0, 0.15), v=16, m="frost_pale")                # omuz
    cyl(0.020, 0.05, (0, 0, 0.205), v=12, m="frost_pale")                       # boyun
    cyl(0.024, 0.03, (0, 0, 0.240), v=12, m="red")                              # kapak
    cyl(0.0515, 0.11, (0, 0, -0.01), v=16, m="white")                           # etiket
    box((0.055, 0.004, 0.05), (0, -0.050, -0.01), m="blue_mid")                 # etiket yazisi blogu


def paper_towel():
    cyl(0.075, 0.24, (0, 0, 0), v=18, m="paper")                                # rulo
    cyl(0.026, 0.26, (0, 0, 0), v=12, m="wood")                                 # ic karton
    box((0.075, 0.003, 0.11), (0.070, -0.030, -0.055), rot=(0, RX(-8), 0), m="paper")   # sarkan uc
    ring(0.076, 0.003, (0, 0, 0.118), m="frost_pale", mseg=18)                  # ust kenar
    ring(0.076, 0.003, (0, 0, -0.118), m="frost_pale", mseg=18)


def straw():
    # tek payet cok ince kalacagi icin hafif acili uclu demet
    for i, (x, a) in enumerate(((-0.020, 6), (0.0, 0), (0.020, -6))):
        col = ("frost", "amber", "green")[i]
        cyl(0.0060, 0.26, (x, 0, 0), rot=(0, RX(a), 0), v=8, m="frost_pale")
        cyl(0.0064, 0.035, (x + math.sin(RX(a)) * 0.11, 0, 0.112), rot=(0, RX(a), 0), v=8, m=col)
        cyl(0.0064, 0.02, (x - math.sin(RX(a)) * 0.12, 0, -0.121), rot=(0, RX(a), 0), v=8, m="white")


def nitrogen():
    cyl(0.070, 0.20, (0, 0, -0.03), v=16, m="steel")                            # kucuk kap
    ring(0.071, 0.007, (0, 0, 0.072), m="steel_dark", mseg=18)                  # agiz kenari
    cyl(0.064, 0.02, (0, 0, 0.060), v=16, m="frost")                            # sivi yuzeyi
    for x, y, z, r in ((-0.045, 0.01, 0.13, 0.040), (0.030, -0.02, 0.16, 0.050),
                       (0.000, 0.02, 0.21, 0.036), (0.060, 0.01, 0.10, 0.030)):
        ball(r, (x, y, z), m="frost_pale", seg=10, ring_count=6)                # buhar bulutlari


def wrong_nail_clipper():
    for s in (-1, 1):
        box((0.030, 0.24, 0.026), (s * 0.034, 0.09, 0), rot=(0, 0, RX(s * 6)), m="red")     # kalin saplar
        box((0.024, 0.13, 0.020), (s * 0.020, -0.10, 0), rot=(0, 0, RX(-s * 9)), m="steel") # cene kollari
        box((0.040, 0.06, 0.014), (s * 0.044, -0.185, 0), rot=(0, 0, RX(-s * 16)), m="steel")  # acik agiz
        box((0.042, 0.018, 0.010), (s * 0.052, -0.215, 0), rot=(0, 0, RX(-s * 16)), m="steel_dark")  # kesici kenar
    cyl(0.022, 0.030, (0, -0.030, 0), rot=(RX(90), 0, 0), v=12, m="steel_dark")             # pim

def wrong_vaccine_syringe():
    cyl(0.026, 0.22, (0, 0, 0), v=14, m="frost_pale")                           # silindir
    cyl(0.020, 0.10, (0, 0, 0.14), v=10, m="white")                             # piston mili
    box((0.055, 0.012, 0.010), (0, 0, 0.196), m="white")                        # basma plakasi
    box((0.060, 0.012, 0.010), (0, 0, -0.106), m="white")                       # parmak flansi
    cone(0.014, 0.006, 0.035, (0, 0, -0.128), v=10, m="steel")                  # uc konik
    cyl(0.0022, 0.09, (0, 0, -0.19), v=6, m="steel")                            # igne
    cyl(0.021, 0.07, (0, 0, -0.02), v=14, m="green")                            # icerik seviyesi


def wrong_milking_cup():
    cone(0.055, 0.042, 0.22, (0, 0, 0), v=16, m="steel")                        # celik govde
    cyl(0.050, 0.05, (0, 0, -0.02), v=16, m="frost_pale")                       # gorus penceresi
    ring(0.056, 0.007, (0, 0, 0.105), m="steel_dark", mseg=18)                  # ust cember
    cyl(0.040, 0.045, (0, 0, 0.130), v=14, m="rubber")                          # meme lastigi
    ring(0.041, 0.006, (0, 0, 0.152), m="rubber", mseg=16)
    cone(0.042, 0.026, 0.04, (0, 0, -0.128), v=14, m="steel_dark")              # alt agiz
    cyl(0.018, 0.09, (0, 0.028, -0.183), rot=(RX(72), 0, 0), v=10, m="rubber")  # sut hortumu

def wrong_pitchfork():
    cyl(0.016, 0.46, (0, 0, 0.10), v=10, m="wood")                              # sap
    box((0.055, 0.016, 0.055), (0, 0, 0.335), m="wood_dark")                    # D-tutamak blogu
    ring(0.040, 0.010, (0, 0, 0.365), rot=(RX(90), 0, 0), m="wood_dark", mseg=14)
    box((0.13, 0.02, 0.035), (0, 0, -0.135), m="steel_dark")                    # boyunduruk
    for i, x in enumerate((-0.048, -0.016, 0.016, 0.048)):                      # 4 dis
        cyl(0.006, 0.20, (x, 0, -0.245), rot=(0, RX((i - 1.5) * 5), 0), v=6, m="steel")
        cone(0.006, 0.0, 0.03, (x + (i - 1.5) * 0.009, 0, -0.355), v=6, m="steel")


def wrong_shovel():
    cyl(0.016, 0.42, (0, 0, 0.14), v=10, m="wood")                              # sap
    box((0.060, 0.018, 0.06), (0, 0, 0.375), m="wood_dark")
    ring(0.042, 0.010, (0, 0, 0.400), rot=(RX(90), 0, 0), m="wood_dark", mseg=14)
    cyl(0.020, 0.07, (0, 0, -0.085), v=10, m="steel_dark")                      # boyun
    box((0.20, 0.015, 0.22), (0, 0.01, -0.215), rot=(RX(8), 0, 0), m="steel")   # kurek agzi
    box((0.205, 0.022, 0.03), (0, 0.004, -0.115), rot=(RX(8), 0, 0), m="steel_dark")   # ust kenar


def wrong_brush():
    box((0.20, 0.09, 0.045), (0, 0, 0.03), m="wood")                            # ahsap govde
    box((0.195, 0.085, 0.02), (0, 0, 0.060), m="wood_dark")                     # ust kavis blogu
    box((0.19, 0.085, 0.055), (0, 0, -0.030), m="rubber")                       # kil kutlesi
    for x in (-0.075, -0.045, -0.015, 0.015, 0.045, 0.075):                     # kil siralari
        box((0.016, 0.085, 0.07), (x, 0, -0.045), m="rubber")
    box((0.055, 0.10, 0.012), (0, 0, 0.072), m="skin")                          # el kayisi


def wrong_feed_bucket():
    cone(0.090, 0.115, 0.22, (0, 0, 0), v=18, m="frost")                        # konik kova
    ring(0.116, 0.008, (0, 0, 0.110), m="blue_mid", mseg=20)                    # ust cember
    ring(0.100, 0.006, (0, 0, 0.175), rot=(0, RX(90), 0), m="steel_dark", mseg=18)   # kulp
    cyl(0.092, 0.012, (0, 0, -0.112), v=18, m="blue_mid")                       # taban
    cyl(0.070, 0.04, (0, 0, 0.075), v=16, m="amber")                            # icindeki yem


def wrong_nose_ring():
    """Burun pensi / burunduruk: pimde birlesen iki kavisli cene, uclarinda yuvarlak
    toplar; asagi uzanan iki sapin ucunda ip gecirilen delikli halkalar.
    (Dosya adi oyunun bekledigi 'wrong-nose-ring' olarak korunur.)"""
    for s in (-1, 1):
        y = s * 0.013                                                   # iki cene derinlikte ayrilir
        arc(s * 0.010, 0.085, 0.055, -78, 118, n=6, r=0.0095, y=y,
            m="chrome", ball_ends=True, bs=0.019)                        # kavisli cene + uc topu
        # sap: pimden asagi, hafif disa acili
        a = RX(-90 + s * 11)
        L = 0.20
        mx, mz = math.cos(a) * L / 2, math.sin(a) * L / 2
        cyl(0.0085, L, (mx, y, 0.025 + mz), rot=(0, math.pi / 2 - a, 0), v=8, m="chrome")
        ex, ez = math.cos(a) * L, 0.025 + math.sin(a) * L
        box((0.030, 0.016, 0.034), (ex, y, ez), rot=(0, 0, RX(s * 11)), m="chrome")   # yassi uc
        ring(0.013, 0.005, (ex, y, ez - 0.004), rot=(RX(90), 0, 0), m="chrome_dark", mseg=14)  # ip deligi
    cyl(0.016, 0.052, (0, 0, 0.030), rot=(RX(90), 0, 0), v=12, m="chrome")   # pim govdesi
    ball(0.019, (0, -0.026, 0.030), m="chrome", seg=12, ring_count=8)        # pim basi
    cyl(0.006, 0.030, (0.012, 0, -0.030), rot=(RX(90), 0, 0), v=8, m="chrome_dark")  # ayar pimi


MODELS = {
    "thermometer": thermometer, "kit-case": kit_case, "ai-gun": ai_gun, "sheath": sheath,
    "straw-forceps": straw_forceps, "straw-cutter": straw_cutter, "glove": glove,
    "lubricant": lubricant, "alcohol": alcohol, "paper-towel": paper_towel,
    "straw": straw, "nitrogen": nitrogen,
    "wrong-nail-clipper": wrong_nail_clipper, "wrong-vaccine-syringe": wrong_vaccine_syringe,
    "wrong-milking-cup": wrong_milking_cup, "wrong-pitchfork": wrong_pitchfork,
    "wrong-shovel": wrong_shovel, "wrong-brush": wrong_brush,
    "wrong-feed-bucket": wrong_feed_bucket, "wrong-nose-ring": wrong_nose_ring,
}


# --- Sahne yonetimi ve export ----------------------------------------------
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.objects):
        for b in list(block):
            if b.users == 0:
                block.remove(b)


def build_and_export(name):
    clear_scene()
    MODELS[name]()
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()                       # tek mesh -> tek draw call
    ob = bpy.context.object
    ob.name = name
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    path = os.path.join(HERE, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True)
    print("[gen] %s.glb  tris=%d  verts=%d" % (name, tris, len(ob.data.vertices)))
    return tris


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = argv or list(MODELS)
    total = 0
    for n in names:
        if n not in MODELS:
            print("[gen] BILINMEYEN MODEL: %s" % n)
            continue
        total += build_and_export(n)
    print("[gen] TAMAM: %d model, toplam %d ucgen" % (len(names), total))


main()
