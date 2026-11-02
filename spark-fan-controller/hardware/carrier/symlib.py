"""Load KiCad library symbols, flatten 'extends', and report pin positions."""
import copy
import os

from sexpr import Q, first, find, parse

KICAD = "C:/Users/OWNER/AppData/Local/Programs/KiCad/10.0/share/kicad"
_libs = {}


def _lib(name):
    if name not in _libs:
        with open(os.path.join(KICAD, "symbols", name + ".kicad_sym"), encoding="utf-8") as f:
            _libs[name] = {s[1]: s for s in find(parse(f.read()), "symbol")}
    return _libs[name]


def load(lib_id):
    """Return a flattened copy of the symbol, named 'Lib:Name' for lib_symbols."""
    lib, name = lib_id.split(":")
    sym = copy.deepcopy(_lib(lib)[name])
    ext = first(sym, "extends")
    if ext:
        parent = copy.deepcopy(_lib(lib)[ext[1]])
        props = {p[1]: p for p in find(sym, "property")}
        out = [x for x in parent if not (isinstance(x, list) and x[0] == "property")]
        out[1] = Q(name)
        for i, x in enumerate(out):
            if isinstance(x, list) and x[0] == "symbol":
                out[i][1] = Q(str(x[1]).replace(ext[1], name, 1))
        parent_props = [p for p in find(parent, "property")]
        merged = [props.get(p[1], p) for p in parent_props]
        merged += [p for k, p in props.items() if k not in {q[1] for q in parent_props}]
        sym = out[:2] + merged + out[2:]
    sym[1] = Q(lib_id)
    return sym


def pins(sym):
    """{number: (x, y, angle, name, etype)} in library coordinates (y up)."""
    out = {}
    for unit in find(sym, "symbol"):
        for p in find(unit, "pin"):
            at = first(p, "at")
            out[str(first(p, "number")[1])] = (float(at[1]), float(at[2]), int(float(at[3])),
                                               str(first(p, "name")[1]), p[1])
    return out


if __name__ == "__main__":
    for lid in ["Regulator_Switching:MT3608", "Transistor_FET:2N7002", "Motor:Fan_4pin",
                "Device:D_Schottky", "Device:LED", "Device:Polyfuse", "power:PWR_FLAG",
                "Mechanical:MountingHole"]:
        print(lid, pins(load(lid)), first(load(lid), "property") and
              [str(p[2]) for p in find(load(lid), "property") if p[1] == "Footprint"])
