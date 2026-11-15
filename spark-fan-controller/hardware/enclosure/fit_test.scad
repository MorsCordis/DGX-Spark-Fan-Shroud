// Quick fit checks for the front shroud, no measuring tools needed
//
// part = "slice": a 20 mm wide end piece of the front shroud (with its corner foot). Put the
//   box in the printed base, push it back, drop the slice onto the front rim at one corner and
//   look at the lip: resting on the box top = this shroud fits; a gap = shroud too tall (add foam
//   or pick the shorter one); won't seat = too short (pick the taller one).
// part = "gauge": a step gauge, 2..9 mm in 0.5 mm steps. Slide steps under the box's body edge
//   (box on a flat desk) until one just fits; that step is the base height d.

part = "slice";              // ["slice", "gauge"]
shroud_dir = "../../../3D Files";
vendor = "Nvidia DGX Spark"; // ["Nvidia DGX Spark", "HP ZGX Nano"]
width = 20;

prefix = vendor == "HP ZGX Nano" ? "HP" : "DGX";

if (part == "slice") {
    intersection() {
        import(str(shroud_dir, "/", vendor, "/", prefix, " Front Shroud.stl"), convexity = 6);
        translate([-79, -500, -500]) cube([width + 1, 1000, 1000]);
    }
} else {
    steps = [for (h = [2 : 0.5 : 9]) h];
    for (i = [0 : len(steps) - 1])
        translate([i * 8, 0, 0]) difference() {
            cube([8, 30, steps[i]]);
            // label: whole millimetres get a notch on top, half steps none
            if (steps[i] == floor(steps[i]))
                translate([4, 26, steps[i] - 0.6]) linear_extrude(1) text(str(steps[i]), size = 4, halign = "center", valign = "center");
        }
}
