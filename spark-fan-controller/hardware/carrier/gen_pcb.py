"""Build spark_fan_carrier.kicad_pcb from design.py with pcbnew (run with KiCad's python).

Board coordinates below are mm from the board's top-left corner (USB end at the top),
offset by ORIGIN on the KiCad canvas.
"""
import uuid

import pcbnew

import design
import symlib

FPLIB = "C:/Users/OWNER/AppData/Local/Programs/KiCad/10.0/share/kicad/footprints/"
ORIGIN = (100.0, 50.0)
W, H = 24.0, 50.0

# RP2040-Zero: 18 x 23.5 mm, USB flush with y=0, header rows 1.38 mm in from its edges,
# first pin 1.59 mm from the USB end (Waveshare drawing).
ZX = 3.0
J1X, J2X, JY = ZX + 1.38, ZX + 18.0 - 1.38, 1.59

# ref: (x, y, rotation_deg)
PLACE = {
    "J1": (J1X, JY, 0), "J2": (J2X, JY, 0),
    # under the Zero (low-profile parts only)
    "R6": (9.0, 6.67, 0), "C5": (12.2, 6.67, 0), "R7": (12.0, 9.21, 0),
    "R4": (9.0, 11.75, 0), "R5": (11.4, 13.6, 270), "Q1": (14.3, 12.7, 0),
    # 5 V in and boost
    "F1": (2.6, 27.0, 270), "C1": (2.6, 32.2, 270), "L1": (7.6, 28.6, 270),
    "U1": (12.5, 31.0, 90), "C6": (14.6, 27.6, 0), "R1": (15.3, 30.0, 270), "R2": (16.0, 32.4, 0),
    "D1": (11.0, 35.8, 180), "C2": (16.9, 35.8, 0), "C3": (16.9, 38.4, 0),
    # indicator, fan, holes
    "R8": (6.4, 39.8, 180), "D2": (3.2, 39.8, 0),
    "J3": (8.2, 45.5, 0), "H1": (3.0, 47.0, 0), "H2": (21.0, 47.0, 0),
}

POWER = {"+5V", "VIN", "SW", "+12V", "GND"}


def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN[0] + x), pcbnew.FromMM(ORIGIN[1] + y))


def sym_uuid(ref):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "/".join((design.PROJECT, "sym", ref))))


board = pcbnew.BOARD()
netinfo = {}
for name in sorted(design.nets()):
    ni = pcbnew.NETINFO_ITEM(board, "/" + name)   # schematic local-label net names
    board.Add(ni)
    netinfo[name] = ni

fps = {}
for ref, (lib_id, value, fp_id, _xy, pinmap, fields) in design.PARTS.items():
    if not fp_id:
        continue
    lib, name = fp_id.split(":")
    fp = pcbnew.FootprintLoad(FPLIB + lib + ".pretty", name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPath(pcbnew.KIID_PATH("/" + sym_uuid(ref)))
    for k, v in fields.items():
        fp.SetField(k, v)
        fp.GetField(k).SetVisible(False)
    fp.Value().SetLayer(pcbnew.F_Fab)
    x, y, rot = PLACE[ref]
    fp.SetPosition(mm(x, y))
    fp.SetOrientationDegrees(rot)
    # References on the fab layer: silkscreen under the Zero would only collide with pads.
    fp.Reference().SetLayer(pcbnew.F_Fab)
    pin_names = symlib.pins(symlib.load(lib_id))
    for pad in fp.Pads():
        num = pad.GetNumber()
        net = pinmap.get(num)
        if net:
            pad.SetNet(netinfo[net])
        elif num in pinmap:
            # Match the schematic's auto-named net for intentionally open pins.
            nc = pcbnew.NETINFO_ITEM(board, "unconnected-(%s-%s-Pad%s)" % (ref, pin_names[num][3], num))
            board.Add(nc)
            pad.SetNet(nc)
    board.Add(fp)
    fps[ref] = fp


def pad_xy(ref, num):
    p = fps[ref].FindPadByNumber(num).GetPosition()
    return (pcbnew.ToMM(p.x) - ORIGIN[0], pcbnew.ToMM(p.y) - ORIGIN[1])


import sys

if "--pads" in sys.argv:
    for ref in fps:
        print(ref, {p.GetNumber(): tuple(round(v, 3) for v in pad_xy(ref, p.GetNumber()))
                    for p in fps[ref].Pads() if p.GetNumber()})
    raise SystemExit


# ---------------------------------------------------------------------------
# Routing. Points are board mm; ("P", ref, pad) snaps to a pad centre.
# ---------------------------------------------------------------------------
F, B = pcbnew.F_Cu, pcbnew.B_Cu

ROUTES = [
    # net, layer, width, points
    ("+5V", F, 0.8, [("P", "J1", "1"), (1.8, 1.59), (1.8, 25.6), ("P", "F1", "1")]),
    ("VIN", F, 0.8, [("P", "F1", "2"), ("P", "C1", "1")]),
    ("VIN", F, 0.8, [("P", "F1", "2"), (4.3, 28.4), (5.95, 26.75), ("P", "L1", "1")]),
    ("VIN", F, 0.5, [("P", "L1", "1"), (12.5, 26.75), ("P", "U1", "5")]),
    ("VIN", F, 0.4, [(12.5, 28.6), (13.45, 28.6), ("P", "U1", "4")]),
    ("VIN", F, 0.5, [(12.5, 27.6), ("P", "C6", "1")]),
    ("SW", F, 0.8, [("P", "L1", "2"), (9.0, 30.45), ("P", "D1", "2")]),
    ("SW", F, 0.6, [(9.0, 32.6), (11.55, 32.6), ("P", "U1", "1")]),
    ("FB", F, 0.3, [("P", "U1", "3"), (13.45, 32.4), ("P", "R2", "1")]),
    ("FB", F, 0.3, [("P", "R1", "2"), (15.3, 32.4)]),
    ("+12V", F, 0.8, [("P", "D1", "1"), ("P", "C2", "1"), ("P", "C3", "1")]),
    ("+12V", F, 0.3, [("P", "C2", "1"), (15.425, 34.3), (17.9, 34.3), (17.9, 29.175), ("P", "R1", "1")]),
    ("+12V", F, 0.5, [("P", "C3", "1"), (15.425, 39.8), ("P", "R8", "1")]),
    ("+12V", F, 0.8, [(10.74, 39.8), ("P", "J3", "2")]),
    ("LED_A", F, 0.3, [("P", "R8", "2"), ("P", "D2", "2")]),
    ("+3V3", F, 0.3, [("P", "J1", "3"), ("P", "R6", "1")]),
    ("TACH", F, 0.3, [("P", "R6", "2"), ("P", "C5", "1")]),
    ("TACH", F, 0.3, [("P", "J1", "4"), ("P", "R7", "1")]),
    ("TACH", F, 0.3, [("P", "R6", "2"), (9.825, 9.21)]),
    ("PWM_MCU", F, 0.3, [("P", "J1", "5"), ("P", "R4", "1")]),
    ("GATE", F, 0.3, [("P", "R4", "2"), ("P", "Q1", "1")]),
    ("GATE", F, 0.3, [("P", "R5", "1"), (11.4, 11.75)]),
    ("TACH_FAN", F, 0.3, [("P", "R7", "2"), (13.9, 9.21)]),
    ("TACH_FAN", B, 0.3, [(13.9, 9.21), (13.9, 42.0), (14.3, 42.6), (14.3, 44.0), ("P", "J3", "3")]),
    ("FAN_PWM", F, 0.3, [("P", "Q1", "3"), (17.4, 12.7)]),
    ("FAN_PWM", B, 0.3, [(17.4, 12.7), (17.4, 43.6), ("P", "J3", "4")]),
    # GND pad stubs to their vias
    ("GND", F, 0.5, [("P", "C1", "2"), (2.6, 34.4)]),
    ("GND", F, 0.5, [("P", "C6", "2"), (15.375, 26.4)]),
    ("GND", F, 0.5, [("P", "U1", "2"), (12.5, 33.35)]),
    ("GND", F, 0.4, [("P", "R2", "2"), (16.3, 33.65)]),
    ("GND", F, 0.8, [("P", "C2", "2"), (19.4, 35.8)]),
    ("GND", F, 0.8, [("P", "C3", "2"), (19.4, 38.4)]),
    ("GND", F, 0.4, [("P", "D2", "1"), (2.412, 41.0)]),
    ("GND", F, 0.4, [("P", "R5", "2"), (11.4, 15.6)]),
    ("GND", F, 0.4, [("P", "Q1", "2"), (13.0, 15.2)]),
    ("GND", F, 0.4, [("P", "C5", "2"), (14.2, 6.67)]),
]

VIAS = [
    ("TACH_FAN", 13.9, 9.21), ("FAN_PWM", 17.4, 12.7),
    ("GND", 2.6, 34.4), ("GND", 15.375, 26.4), ("GND", 12.5, 33.35), ("GND", 16.3, 33.65),
    ("GND", 19.4, 35.8), ("GND", 19.4, 38.4), ("GND", 2.412, 41.0), ("GND", 11.4, 15.6),
    ("GND", 13.0, 15.2), ("GND", 14.2, 6.67),
    # stitching
    ("GND", 22.8, 26.0), ("GND", 22.8, 33.0), ("GND", 22.8, 41.0), ("GND", 6.0, 36.6),
    ("GND", 4.6, 43.0), ("GND", 10.5, 4.0), ("GND", 15.5, 4.0), ("GND", 10.0, 17.5),
    ("GND", 15.5, 19.0),
]


def resolve(pt):
    return pad_xy(pt[1], pt[2]) if pt[0] == "P" else pt


for net, layer, width, pts in ROUTES:
    xy = [resolve(p) for p in pts]
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(mm(x0, y0))
        t.SetEnd(mm(x1, y1))
        t.SetWidth(pcbnew.FromMM(width))
        t.SetLayer(layer)
        t.SetNet(netinfo[net])
        board.Add(t)

for net, x, y in VIAS:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(mm(x, y))
    v.SetDrill(pcbnew.FromMM(0.3))
    v.SetWidth(pcbnew.FromMM(0.6))
    v.SetNet(netinfo[net])
    board.Add(v)

# Board outline
corners = [(0, 0), (W, 0), (W, H), (0, H)]
for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(mm(x0, y0))
    seg.SetEnd(mm(x1, y1))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(pcbnew.FromMM(0.1))
    board.Add(seg)

# GND pour, both layers
for layer in (F, B):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(netinfo["GND"])
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        ol.Append(mm(x, y))
    board.Add(z)


def silk(text, x, y, layer=pcbnew.F_SilkS, size=0.8, rot=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


silk("SPARK FAN CARRIER", W / 2, 26.0, pcbnew.B_SilkS, 1.0)
silk("rev " + design.REV + "  2026-10", W / 2, 28.0, pcbnew.B_SilkS, 0.8)
silk("GP28 PWM / GP29 TACH", W / 2, 30.0, pcbnew.B_SilkS, 0.8)
silk("FAN 1=GND 2=12V 3=TACH 4=PWM", W / 2, 41.0, pcbnew.B_SilkS, 0.8)
silk("12V", 3.2, 38.3, pcbnew.F_SilkS, 0.8)
# Diode polarity: "+" under the anode, "-" under the cathode (pad 1 is K on both)
for ref, dy in (("D1", 2.3), ("D2", 2.1)):
    for num, mark in (("1", "-"), ("2", "+")):
        x, y = pad_xy(ref, num)
        silk(mark, x, y + dy, pcbnew.F_SilkS, 1.0)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(design.PROJECT + ".kicad_pcb")
print("saved", design.PROJECT + ".kicad_pcb")
