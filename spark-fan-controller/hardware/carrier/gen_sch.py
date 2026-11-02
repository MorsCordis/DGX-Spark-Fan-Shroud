"""Write spark_fan_carrier.kicad_sch from design.py (labels on every pin, no wires)."""
import uuid

import design
import symlib
from sexpr import Q, dump

ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, design.PROJECT))


def uid(*key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "/".join((design.PROJECT,) + key)))


def font(hide=False, justify=None):
    e = ["effects", ["font", ["size", 1.27, 1.27]]]
    if justify:
        e.append(["justify"] + justify)
    if hide:
        e.append(["hide", "yes"])
    return e


def prop(name, value, x, y, hide=False):
    p = ["property", Q(name), Q(value), ["at", x, y, 0]]
    if hide:
        p.append(["hide", "yes"])
    return p + [font()]


# Label angle / justification for a pin pointing away from the body.
LABEL_DIR = {0: (180, ["right", "bottom"]), 180: (0, ["left", "bottom"]),
             90: (270, ["right", "bottom"]), 270: (90, ["left", "bottom"])}

lib_symbols, items = {}, []
for ref, (lib_id, value, fp, (sx, sy), pinmap, fields) in design.PARTS.items():
    sym = symlib.load(lib_id)
    lib_symbols[lib_id] = sym
    pins = symlib.pins(sym)
    is_power = lib_id.startswith("power:")
    inst = ["symbol", ["lib_id", Q(lib_id)], ["at", sx, sy, 0], ["unit", 1],
            ["exclude_from_sim", "no"], ["in_bom", "no" if is_power or ref.startswith("H") else "yes"],
            ["on_board", "no" if is_power else "yes"], ["dnp", "no"], ["uuid", uid("sym", ref)],
            prop("Reference", ref, sx + 2.54, sy - 6.35, hide=is_power),
            prop("Value", value, sx + 2.54, sy + 6.35),
            prop("Footprint", fp, sx, sy, hide=True),
            prop("Datasheet", "", sx, sy, hide=True)]
    for k, v in fields.items():
        inst.append(prop(k, v, sx, sy, hide=True))
    for num in pins:
        inst.append(["pin", Q(num), ["uuid", uid("pin", ref, num)]])
    inst.append(["instances", ["project", Q(design.PROJECT),
                               ["path", Q("/" + ROOT), ["reference", Q(ref)], ["unit", 1]]]])
    items.append(inst)

    for num, (px, py, ang, _, etype) in pins.items():
        x, y = round(sx + px, 2), round(sy - py, 2)
        if num not in pinmap and is_power:
            continue
        net = pinmap.get(num)
        if net is None:
            if etype != "no_connect":
                items.append(["no_connect", ["at", x, y], ["uuid", uid("nc", ref, num)]])
            continue
        a, just = LABEL_DIR[ang]
        items.append(["label", Q(net), ["at", x, y, a], ["fields_autoplaced", "yes"],
                      font(justify=just), ["uuid", uid("lbl", ref, num)]])

for i, ((x, y), text) in enumerate(design.NOTES):
    items.append(["text", Q(text), ["exclude_from_sim", "no"], ["at", x, y, 0],
                  font(justify=["left", "bottom"]), ["uuid", uid("note", str(i))]])

sch = ["kicad_sch", ["version", 20250610], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
       ["uuid", ROOT], ["paper", Q("A4")],
       ["title_block", ["title", Q(design.TITLE)], ["date", Q("2026-10-22")], ["rev", Q(design.REV)]],
       ["lib_symbols"] + list(lib_symbols.values())] + items + \
      [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]]]

with open(design.PROJECT + ".kicad_sch", "w", encoding="utf-8", newline="\n") as f:
    f.write(dump(sch) + "\n")
print("wrote", design.PROJECT + ".kicad_sch", len(design.PARTS), "symbols")
