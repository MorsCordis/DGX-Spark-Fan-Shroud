"""Export JLCPCB fabrication + assembly files into fab/ (run after gen_sch.py and gen_pcb.py).

fab/spark_fan_carrier_gerbers.zip   upload as the PCB
fab/bom_jlc.csv, fab/cpl_jlc.csv    upload for SMT assembly (top side)
The THT sockets, fan header and mounting holes are excluded from assembly.
"""
import csv
import os
import shutil
import subprocess

import design

CLI = "C:/Users/OWNER/AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"
PCB = design.PROJECT + ".kicad_pcb"
SCH = design.PROJECT + ".kicad_sch"
OUT = "fab"
GERB = os.path.join(OUT, "gerbers")
NOT_ASSEMBLED = {"J1", "J2", "J3", "H1", "H2"}

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(GERB)


def run(*args):
    subprocess.run([CLI, *args], check=True, stdout=subprocess.DEVNULL)


run("pcb", "export", "gerbers", "--layers",
    "F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts", "-o", GERB + "/", PCB)
run("pcb", "export", "drill", "--format", "excellon", "--generate-map", "--map-format", "pdf",
    "-o", GERB + "/", PCB)
shutil.make_archive(os.path.join(OUT, design.PROJECT + "_gerbers"), "zip", GERB)

# KiCad vs JLC part orientation, checked in JLC's placement preview 2026-10-30
# (Q1 C8545 sat 180 deg off, U1 C84817 90 deg CCW of correct)
JLC_ROT = {"SOT-23": 180, "SOT-23-6": -90}

pos = os.path.join(OUT, "pos.csv")
run("pcb", "export", "pos", "--side", "front", "--format", "csv", "--units", "mm", "-o", pos, PCB)
with open(pos, newline="") as f, open(os.path.join(OUT, "cpl_jlc.csv"), "w", newline="") as g:
    w = csv.writer(g)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in csv.DictReader(f):
        if r["Ref"] not in NOT_ASSEMBLED:
            rot = (float(r["Rot"]) + JLC_ROT.get(r["Package"], 0) + 180) % 360 - 180
            w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm", "Top", f"{rot:.6f}"])
os.remove(pos)

# BOM straight from design.py (same source the schematic was generated from)
groups = {}
for ref, (lib_id, value, fp, _xy, _pins, fields) in design.PARTS.items():
    if ref.startswith("#") or ref in NOT_ASSEMBLED:
        continue
    key = (value, fp.split(":")[1], fields.get("LCSC", ""), fields.get("MPN", ""))
    groups.setdefault(key, []).append(ref)
with open(os.path.join(OUT, "bom_jlc.csv"), "w", newline="") as g:
    w = csv.writer(g)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "MPN / note"])
    for (value, fp, lcsc, mpn), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([value, ",".join(sorted(refs)), fp, lcsc, mpn])

# Hand-soldered parts
with open(os.path.join(OUT, "bom_hand_solder.csv"), "w", newline="") as g:
    w = csv.writer(g)
    w.writerow(["Designator", "Part", "Note"])
    w.writerow(["J1,J2", "1x9 female header, 2.54 mm, ~8.5 mm tall", "RP2040-Zero plugs in here"])
    w.writerow(["J3", "4-pin PWM fan header (Molex 47053-1000 style)", "pin 1 = GND (square pad)"])
    w.writerow(["H1,H2", "M2.5 screws/standoffs", "enclosure mounting"])
print("fab outputs in", os.path.abspath(OUT))
