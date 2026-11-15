v2 PARTS (2026-11-14) - fan guard for the DGX Spark shroud + Spark Fan Carrier case
Sources: ../../fan_guard.scad and ../../carrier_case.scad (v1 kept as *_v1.scad)

All parts print without supports, in the orientation they are exported in. Do not scale.
PETG is the better choice for the snap parts; PLA works (strains are ~1.1-1.5 %).

FAN GUARD (sits inside the shroud's fan tube, under the fan; no magnets or screws)
  fan_guard_guard.stl   plate down. Corners notched 7 mm to clear the shroud legs. 3+ perimeters on the rim. The ratchet teeth on two inner
                        walls have 45 deg undersides and print fine without supports.
  fan_guard_plug.stl    grid down. The two fingers are 1.0 mm walls; make sure the slicer
                        prints them (no "thin wall" gaps).
  filter_template.svg   1:1 octagon to cut the filter (112.2 mm across flats).

  Fit: drop the guard into the tube from above so it rests on the bottom ledges, set the fan
  on it, put the filter in the pocket from below, push the plug in until it clicks against the
  filter. Remove: pinch the two grip tabs toward the centre and pull.
  Rim hangs ~6.7 mm below the shroud bottom, except two 36 mm tooth tabs (15.3 mm) on the
  ratchet sides (shroud bottom is ~33 mm above the desk on the
  65 mm legs). Teeth too stiff: lower tooth_h; too loose: raise it or finger_t.

CARRIER CASE
  carrier_case_base.stl floor down.
  carrier_case_lid.stl  top face down (it is ROTATED, not mirrored: the text reads correctly).
  Board: press it straight down; the four wall hooks click over the long edges.
  Lid: press down until both side latches click. To open, push each latch bump in through
  its side window and lift.
  Outer size 28.8 x 54.8 x 25.8 mm (1.5 mm taller than v1: standoffs went 3 -> 4.5 mm so the
  hooks are long enough to flex).

ASSEMBLY VIEW
  ../../full_assembly.scad: Spark + upstream shroud + legs + fan + v2 guard/plug + case.
  Open in OpenSCAD, F5, toggle parts / cut / explode in Window > Customizer.
  Legs sit in the open tube corners (53..68 mm from the tube centre), per the upstream files.
