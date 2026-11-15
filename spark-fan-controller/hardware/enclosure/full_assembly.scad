// Full assembly viewer: DGX Spark on the upstream fan shroud (hyudryu/DGX-Spark-Fan-Shroud, MIT)
// with the four legs, the 120 mm fan, the v2 fan guard + filter plug, and the v2 carrier case
// beside it. Nothing here is printed. Open in OpenSCAD, press F5, orbit with the mouse;
// toggle parts in Window > Customizer. Shroud frame: tube centre (0, 262), bottom ledge
// z = -35..-33, desk at z = -68.

/* [Show] */
show_shroud = true;
show_legs = true;
show_box = true;          // Printables 1:1 DGX Spark model
show_fan = true;
show_guard = true;
show_plug = true;
show_case = true;
filter = 6.5;             // filter thickness in the pocket, 0 .. 6.5
cut = "none";             // ["none", "x", "y"] slice through the fan tube centre
explode = 0;              // [0:5:80] pull the guard/plug down out of the tube

use <fan_guard.scad>
use <carrier_case.scad>

tube_c = [0, 262];
ledge_top = -33;
fan_t = 25;
desk = -68;

module shroud() color([0.15, 0.15, 0.17]) import("ref/upstream_dgx_fan_shroud.stl", convexity = 6);
// The leg STL is modelled at the tube's -x/-y corner, 25 mm off in y: its 15 mm head drops into
// the corner socket (53..68 mm from the tube centre) and the post runs down past the open corner.
module legs()
    color([0.25, 0.25, 0.28]) for (sx = [0, 1], sy = [0, 1])
        translate([tube_c[0], tube_c[1], 0]) mirror([sx, 0, 0]) mirror([0, sy, 0])
            translate([0, 25, 0]) import("ref/upstream_shroud_leg.stl", convexity = 6);
module box()
    color([0.75, 0.66, 0.45, 0.6]) translate([0, 335 - 75, 15 + 23]) rotate([0, 0, -90])
        import("ref/nvidia_dgx_spark_printables_1512927.stl", convexity = 6);
module fan()
    color([0.55, 0.35, 0.25]) translate([tube_c[0], tube_c[1], ledge_top + 3]) difference() {
        linear_extrude(fan_t) offset(4) offset(-4) square(119, center = true);
        translate([0, 0, -1]) cylinder(r = 58, h = fan_t + 2, $fn = 96);
    }
// guard model z grows away from the fan, i.e. down: plate top (z = 0) sits at ledge_top + 3
module installed() translate([tube_c[0], tube_c[1], ledge_top + 3 - explode]) mirror([0, 0, 1]) children();
module filter_pad()
    if (filter > 0) color([0.9, 0.9, 0.85, 0.7]) installed() translate([0, 0, 3]) linear_extrude(filter)
        intersection() { square(2 * 55.9, center = true); rotate(45) square(92 * sqrt(2), center = true); }
module case_()
    translate([110, 200, desk]) { base(); color("SteelBlue", 0.9) lid(); }

module all() {
    if (show_shroud) shroud();
    if (show_legs) legs();
    if (show_box) box();
    if (show_fan) fan();
    if (show_guard) color([0.2, 0.6, 0.3]) installed() guard();
    if (show_plug) color([0.85, 0.5, 0.1]) installed() translate([0, 0, explode * 0.6]) plug_installed(filter);
    filter_pad();
    if (show_case) case_();
    if (cut == "none") %translate([-150, 120, desk - 1]) cube([400, 280, 1]);
}

if (cut == "x") intersection() { all(); translate([0, -500, -500]) cube([1000, 1000, 1000]); }
else if (cut == "y") intersection() { all(); translate([-500, tube_c[1], -500]) cube([1000, 1000, 1000]); }
else all();
