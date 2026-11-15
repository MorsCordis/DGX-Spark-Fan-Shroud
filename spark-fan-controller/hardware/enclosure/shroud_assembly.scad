// Assembly check: GB10 box in the DGX-Spark-Fan-Shroud tray, with front shroud and stacking legs
//
// Imports the upstream STLs in their own coordinates (they share one frame: tray front rim at
// y = 164, floor ledge at z = 0) and adds a box. Nothing here is printed; it is for looking at
// fit and the air path. Use cut to slice it open.
//
// How a box sits: the tray has 15 mm shelves along both sides (front half only, y < 265) and
// across the rear (y 327..335). The gap between the side shelves is 142 mm, so any 150 mm box
// rests its body on them at z = 15, and feet or a base shorter than 15 mm hang into the space
// below. That space is the plenum: closed by the shelves at the sides and rear, open only at
// the front, where the front shroud turns the air up into the front vents. Its lip has to sit
// on the box top to seal, so the lip height must equal 15 + body height (feet excluded):
//   DGX / Lenovo / Gigabyte front: lip underside z = 60.5  ->  45.5 mm body (DGX: 51.5 total,
//                                  6 mm base dropping into the fan opening)
//   HP front:                      lip underside z = 66.0  ->  51 mm body, flat bottom
// Leaks found by voxel trace (shroud_flow notes): ~1 mm gaps beside the box in the rear half,
// where there is no side shelf, and behind the box; the box can also slide ~9 mm front-back.

/* [Files] */
// folder holding the upstream "3D Files" (this path works from the fork's spark-fan-controller/ folder)
shroud_dir = "../../../3D Files";
vendor = "Nvidia DGX Spark";   // ["Nvidia DGX Spark", "HP ZGX Nano"]
// 1:1 DGX Spark by SchwickSchwimmer, printables.com/model/1512927, CC BY-NC-SA
dgx_stl = "ref/nvidia_dgx_spark_printables_1512927.stl";

/* [Box] */
model = "dgx";                 // ["dgx", "block"] the Printables DGX Spark, or a plain block
block = [150, 150, 50.5];      // block: Veriton GN100 spec, total height incl. feet
foot = 0;                      // block: foot height under the body                 MEASURE
box_rear_y = 335;              // pushed back against the pocket's rear wall
shelf_z = 15;

/* [Show] */
show_front = true;
show_stack = false;            // stacking legs clash with the front shroud lip (front legs)
cut = "none";                  // ["none", "x", "y"] slice at x = cut_at (side view) or y = cut_at
cut_at = 0;

// HP's front shroud STL is modelled 50 mm further forward than the DGX one
hp_shift = vendor == "HP ZGX Nano" ? 50 : 0;
prefix = vendor == "HP ZGX Nano" ? "HP" : "DGX";
body = block[2] - foot;
box_top = model == "dgx" ? shelf_z + 45.5 : shelf_z + body;
echo(box_top = box_top, lip_underside = vendor == "HP ZGX Nano" ? 66.0 : 60.5);

module part(name) import(str(shroud_dir, "/", vendor, "/", name, ".stl"), convexity = 6);

module box() {
    if (model == "dgx")
        // model: front (+x) faces the tray front (-y); body underside (z = -23) on the shelves
        translate([0, box_rear_y - 75, shelf_z + 23]) rotate([0, 0, -90]) import(dgx_stl, convexity = 6);
    else
        translate([-block[0] / 2, box_rear_y - block[1], shelf_z]) cube([block[0], block[1], body]);
}

module assembly() {
    color([0.15, 0.15, 0.17]) part(str(prefix, " Fan Shroud"));
    color([0.75, 0.66, 0.45, 0.6]) box();
    if (show_front)
        color([0.85, 0.35, 0.1]) translate([0, hp_shift, 0]) part(str(prefix, " Front Shroud"));
    // frame plate underside (z = -70 in its file) on the box top, centred on the box
    if (show_stack)
        color([0.1, 0.45, 0.8]) translate([0, box_rear_y - 75 + 25, box_top + 70]) part("Stacking Legs");
}

if (cut == "x")
    intersection() { assembly(); translate([cut_at, -500, -500]) cube([500, 1000, 1000]); }
else if (cut == "y")
    intersection() { assembly(); translate([-500, cut_at, -500]) cube([1000, 500, 1000]); }
else
    assembly();
