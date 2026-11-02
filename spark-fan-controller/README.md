# Spark fan controller

External 120 mm fan control for NVIDIA DGX Spark boxes in the
[DGX-Spark-Fan-Shroud](https://github.com/hyudryu/DGX-Spark-Fan-Shroud) (fork: MorsCordis).
The host service feeds the fan forward from GPU/CPU load with a temperature fallback.

## Layout

| Path | What |
|---|---|
| `host/spark_fan.py`, `host/spark-fan.service` | Host controller (runs on each Spark). Load-anticipating curve + thermal fallback, serial `DUTY 0..255` |
| `firmware/main_pwm_carrier.py` | MicroPython for the **Spark Fan Carrier** (GP28 PWM via open-drain FET, GP29 tach) |
| `firmware/main_x9c103.py` | Original repo firmware for the X9C103 + Owltree build (box #1) |
| `hardware/carrier/` | Spark Fan Carrier rev A: KiCad 10 schematic + PCB, generated from `design.py` |
| `hardware/carrier/fab/` | JLCPCB upload: `spark_fan_carrier_gerbers.zip`, `bom_jlc.csv`, `cpl_jlc.csv`, `bom_hand_solder.csv` |
| `hardware/enclosure/carrier_case.scad` | Parametric 3D-printed case for the carrier (+ `stl/`) |
| `hardware/enclosure/fan_guard.scad` | Bolt-on 120 mm intake guard + filter pocket + retainer (+ `stl/`, `stl/filter_template.svg`) |
| `hardware/enclosure/x9c103_box.scad` | Case for the original three-board build |
| `tests/` | `prefill_stress.py` (long-context prefill ramp via vLLM), `llm_stress.py`, `cooling_test.py` |
| `docs/` | Forum write-ups, stress logs, build guide for the X9C103 build |

## Spark Fan Carrier (rev A)

RP2040-Zero plugs into two 1x9 sockets. Its USB 5 V feeds an MT3608 boost to 12.36 V
(100k/5.1k feedback) for a 4-pin PWM fan header. GP28 drives fan pin 4 through a 2N7002
(open drain, inverted, gate pulled down, so a dead or unflashed RP2040 means full speed).
GP29 reads the tach through 1k with a 10k pull-up and 1 nF filter. 1.5 A PTC on the 5 V input,
green LED on 12 V. 24 x 50 mm, two layers, GND pour both sides, two M2.5 holes.

Rebuild everything (KiCad's bundled python):

```
cd hardware/carrier
"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe" gen_sch.py
"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe" gen_pcb.py
"%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe" fab.py
```

`design.py` is the single source for parts and nets; `gen_pcb.py` holds placement and routing.
Last check: ERC 0 violations, DRC 0 errors / 0 unconnected, schematic parity clean (remaining
warnings are silkscreen overlaps from the stock socket footprints).

Ordering at JLC (the board has SMD parts that are NOT practical to hand-solder, including the
MT3608, which DigiKey doesn't carry):
1. Upload `fab/spark_fan_carrier_gerbers.zip` (2 layers, 1.6 mm).
2. **Turn on "PCB Assembly"** below the board options. Without it JLC ships bare boards.
   Economic PCBA, top side, PCBA qty can be lower than the board qty.
3. Upload `fab/bom_jlc.csv` (BOM) and `fab/cpl_jlc.csv` (placement).
4. Check every part is matched, then check rotations in the placement preview (D1, D2, U1, Q1).

Before ordering:
- All 16 LCSC numbers in `fab/bom_jlc.csv` checked against JLC part pages on 2026-10-24
  (values, packages and ratings match). MT3608 and the LED are Extended parts.
- Check part rotations in JLC's placement preview (KiCad and JLC disagree on some footprints).
- J1/J2 (1x9 female, ~8.5 mm) and J3 (4-pin fan header) are hand-soldered.

Firmware: flash MicroPython, copy `firmware/main_pwm_carrier.py` to the board as `main.py`.
`host/spark_fan.py` works unchanged and now gets real `RPM` readings.

## Enclosure

`carrier_case.scad`: base + friction-fit lid, prints without supports (lid prints upside down).
USB-C opening, fan-cable slot, mounting ears, pinholes over BOOT/RESET. No screws: pegs on the
standoffs pass through H1/H2 and posts on the lid clamp the board (`fix = "screw"` restores
M2.5 self-tap pilots). Light pipes: Bivar PLPC2 press-fit from the top of the lid
(PLPC2-3MM over the Zero's RGB LED, PLPC2-500 over the 12 V LED, 2.0 mm hole with Bivar's
countersink); `pipes = "filament"` switches to clear 1.75 mm filament. Values marked `MEASURE`
(socket height, Zero LED/button positions) should be checked against real parts.
Outer size ~28.8 x 54.8 x 24.3 mm.

## Purchased parts

`hardware/bom_digikey_per_build.csv` is the DigiKey order for one build (carrier through-hole
parts, light pipes, fan guard magnets + filter, cable). Upload it in DigiKey's BOM Manager and
set the number of assemblies. The JLC-assembled SMD parts are in
`hardware/carrier/fab/bom_jlc.csv`; `hardware/carrier/fab/bom_digikey_smd.csv` is a DigiKey
fallback for hand assembly (no MT3608: DigiKey doesn't carry it; get it from LCSC C84817). RP2040-Zero boards come from Waveshare (not on DigiKey).

## Fan guard + filter

`fan_guard.scad`: hex grille plate that snaps onto the fan's intake side magnetically.
Default (`mount = "screw_head"`): drive the fan's bundled steel screws into the intake end of
the four holes; their heads sit in recesses on the guard's fan face (which also locate it) and
a 1/4" x 1/8" disc magnet (Radial Magnets 8193) sealed above each recess grabs them. Print fan-face down, pause at
z = 6.8 mm, drop the magnets in, resume. Measure the screw head (`head`, marked MEASURE) first.
`mount = "magnet"` glues 4 mm magnets into the holes instead (`stl/fan_guard_magnet.stl`, pause
at 4.0 mm; set polarity by sticking pairs together and marking the exposed face).
`mount = "screw"` is the bolt-on version (`stl/fan_guard_screw.stl`). An octagonal rim forms a pocket for a filter
up to `filter_max` (6.5 mm) thick; the retainer grid's skirt slides over the rim and stops on
the filter, so thin mesh and 1/4" foam both work. Adds 11.1 mm below the fan. Cut the
filter from `stl/filter_template.svg` (print at 100 %). Both parts print flat, no supports.

## To do

- [ ] Order carrier rev A, build, flash, bench test (12 V rail, PWM sweep, tach)
- [ ] Print + fit-check fan guard (fan hole diameter vs magnet, retainer `fit`)
- [ ] Multi-box dashboard (status endpoint in `spark_fan.py`)
- [ ] Filter-on vs filter-off prefill run at 2400 MHz
- [ ] Carrier, case, fan guard and carrier firmware stay private (possible product). Only the load-boost software is public (fork branch `feature/load-boost-controller`)
