// Intake guard + filter pocket for the 120 mm fan in the DGX Spark fan shroud, v2
// (FDM, no supports). v1 (magnet / screw-head mounts, friction retainer) is fan_guard_v1.scad.
//
// Where it sits: inside the shroud's fan tube, UNDER the fan. The tube is 120 mm square
// inside, made of four wall plates with open corners, and each wall has a 2 mm ledge at the
// bottom (opening 116 mm). The guard plate rests on those ledges and the fan rests on the
// guard, so no magnets or screws are needed. The filter rim hangs down through the 116 mm
// opening.
//
// Stack, from the fan outward (model z grows away from the fan, i.e. DOWN when installed):
//   guard plate  flat hex grille, 119.4 mm square, rests on the tube ledges
//   rim          octagonal filter pocket; sawtooth ratchet teeth on two inner walls
//   plug         grid that presses the filter in from below, held by two flex fingers whose
//                pawls click along the teeth (~1.25 mm steps)
//
// Why a plug and not v1's outer skirt: a skirt over the rim only gets the rim below the
// 2 mm ledge, ~4 mm with a 1/4" filter, and fingers that short are too stiff to flex
// over a ratchet tooth in PLA. Inside the rim the fingers can be 7 mm long (~1.5 % strain).
//
// Fit: push the plug in until it meets the filter; it clicks every pitch. To remove, pinch
// the two grip tabs toward the centre and pull. Works from bare mesh up to filter_max.
// Cut the filter with part = "template". If the clicks are too stiff, lower tooth_h;
// too weak, raise it (keep strain sane) or thicken finger_t.

part = "print";          // "print", "guard", "plug", "assembled", "section", "template"

/* [Shroud tube] */
tube = 120;                  // fan tube inside, square
ledge_open = 116;            // opening between the bottom ledges
ledge_h = 2.0;               // ledge height (the rim passes through it)
ledge_clr = 0.3;             // rim-to-ledge clearance, per side
plate_clr = 0.3;             // plate-to-tube clearance, per side
leg_in = 53;                 // the walls end here; the shroud legs fill the corners beyond
leg_clr = 0.5;               // plate corner notch clearance to the legs

/* [Guard] */
plate_t = 3.0;               // grille plate thickness (rib depth)
plate_r = 4;                 // plate corner radius
cell = 10;                   // hex cell across flats
rib = 1.2;
open_r = 56;                 // grille radius over the fan opening
rim_t = 1.6;
chamfer = 92;                // pocket corner clip: |x| + |y| <= chamfer
filter_max = 6.5;            // deepest filter the pocket takes (1/4" foam)

/* [Plug] */
plug_t = 1.6;                // grid thickness
plug_cell = 18;
plug_border = 3;             // solid band around the grid edge
plug_fit = 0.3;              // plug-to-rim clearance on the plain sides

/* [Ratchet] */
tooth_h = 0.45;              // tooth height (how far the finger must flex, less 0.05)
lock_len = 0.45;             // = tooth_h gives a 45 deg locking face (printable overhang)
ramp_len = 0.8;              // ramp face along z (~60 deg from horizontal)
finger_len = 7;              // finger length above the grid
finger_t = 1.0;
finger_w = 28;
finger_clr = 0.25;           // finger outer face to tooth tips
grip = 2.5;                  // pinch tab reach, inward

$fn = 48;

r2 = sqrt(2);
plate = tube - 2 * plate_clr;
ro = ledge_open / 2 - ledge_clr;           // rim outer half-width
ri = ro - rim_t;                            // rim inner half-width (pocket)
pitch = lock_len + ramp_len;
xf = ri - tooth_h - finger_clr;             // finger outer face
pawl = tooth_h + finger_clr - 0.05;         // pawl reach past the finger face
pawl_ramp = pawl * ramp_len / tooth_h;
zt = plug_t + finger_len;                   // finger tip, plug coordinates
// Pawl tip height above the filter top; the teeth cover filter = 0 .. filter_max.
tip_off = zt - pawl;
z_lo = plate_t + tip_off - pitch;
n_teeth = ceil((filter_max + 2 * pitch) / pitch);
rim_top = z_lo + n_teeth * pitch + 0.6;
teeth_w = finger_w + 4;
// The rim only needs full depth where the teeth are (two 36 mm tabs, +-x). Elsewhere it stops
// just past the plug grid at the thickest filter.
rim_short = plate_t + filter_max + plug_t + 0.6;
tab_w = teeth_w + 4;

echo(str("plate ", plate, " mm; rim outer ", 2 * ro, " across flats (ledge opening ", ledge_open, ")"));
echo(str("rim depth below the plate ", rim_top - plate_t, " mm; hangs ", rim_top - plate_t - ledge_h,
         " mm below the shroud bottom; ", n_teeth, " teeth, pitch ", pitch, " mm"));
echo(str("plain rim hangs ", rim_short - plate_t - ledge_h, " mm below the shroud bottom; tooth tabs ",
         rim_top - plate_t - ledge_h, " mm"));
echo(str("finger strain ~", round(1500 * finger_t * (tooth_h + 0.05) / (finger_len * finger_len)) / 10, " %"));

// Octagon: half-widths h = [x, y], corners clipped at |x| + |y| <= c.
module octagon(h, c) {
    intersection() {
        square([2 * h[0], 2 * h[1]], center = true);
        rotate(45) square(c * r2, center = true);
    }
}

module hex_holes(flat, web, radius) {
    p = flat + web;
    n = ceil(radius / p) + 1;
    for (i = [-n:n], j = [-n:n])
        translate([i * p * cos(30), (j + (i % 2 == 0 ? 0 : 0.5)) * p])
            circle(r = flat / sqrt(3), $fn = 6);
}

module grille_2d(flat, web, radius) {
    intersection() {
        circle(r = radius, $fn = 120);
        hex_holes(flat, web, radius);
    }
}

// Sawtooth on the +x inner wall, in the x-z plane, extruded along y.
// One polygon: back edge buried 0.5 mm in the wall, then the sawtooth face.
module teeth_2d() {
    zn = z_lo + n_teeth * pitch;
    polygon(concat(
        [[ri + 0.5, zn], [ri + 0.5, z_lo]],
        [for (k = [0:n_teeth - 1]) each [
            [ri, z_lo + k * pitch],
            [ri - tooth_h, z_lo + k * pitch + lock_len]]],
        [[ri, zn]]
    ));
}

module guard() {
    linear_extrude(plate_t) difference() {
        offset(plate_r) offset(-plate_r) square(plate, center = true);
        grille_2d(cell, rib, open_r);
        // corner notches: the legs pass up through the open tube corners
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (leg_in - leg_clr), sy * (leg_in - leg_clr)])
                rotate(sx > 0 ? (sy > 0 ? 0 : 270) : (sy > 0 ? 90 : 180)) square(20);
    }
    translate([0, 0, plate_t]) linear_extrude(rim_short - plate_t) difference() {
        octagon([ro, ro], chamfer + rim_t * r2);
        octagon([ri, ri], chamfer);
    }
    for (s = [0, 1]) mirror([s, 0, 0]) {
        rotate([90, 0, 0]) linear_extrude(teeth_w, center = true) teeth_2d();
        // tooth tab, ends chamfered 45 deg so it prints cleanly
        translate([ri, 0, rim_short - 0.01]) rotate([90, 0, 90]) linear_extrude(rim_t)
            polygon([[-tab_w / 2 - (rim_top - rim_short), 0], [tab_w / 2 + (rim_top - rim_short), 0],
                     [tab_w / 2, rim_top - rim_short + 0.01], [-tab_w / 2, rim_top - rim_short + 0.01]]);
    }
}

// Plug in its own frame: grid at z = 0..plug_t (fan side down), fingers up.
module finger_2d() {
    // finger, pawl on the outer face (+x), pinch tab inward at the tip
    polygon([
        [xf - finger_t, 0], [xf, 0], [xf, zt - pawl - pawl_ramp],
        [xf + pawl, zt - pawl], [xf, zt],
        [xf - finger_t - grip, zt], [xf - finger_t - grip, zt - 0.8],
        [xf - finger_t, zt - 0.8 - grip]
    ]);
}

module plug() {
    hp = [xf, ri - plug_fit];
    cp = chamfer - plug_fit * r2;
    linear_extrude(plug_t) difference() {
        octagon(hp, cp);
        intersection() {
            octagon([hp[0] - plug_border, hp[1] - plug_border], cp - plug_border * r2);
            hex_holes(plug_cell, rib, ri);
        }
    }
    for (s = [0, 1]) mirror([s, 0, 0])
        rotate([90, 0, 0]) linear_extrude(finger_w, center = true) finger_2d();
}

module plug_installed(filter = filter_max) {
    translate([0, 0, plate_t + filter]) plug();
}

module ghost_fan() {
    translate([0, 0, -25]) difference() {
        linear_extrude(25) offset(4) offset(-4) square(120, center = true);
        translate([0, 0, -1]) cylinder(r = 58, h = 27);
    }
}

// Tube walls and bottom ledges, for looking only. Model z points down when installed, so the
// ledges the plate rests on sit at z = plate_t .. plate_t + ledge_h, beside the rim.
module ghost_tube() {
    for (a = [0:90:270]) rotate(a) {
        translate([-leg_in, tube / 2, -30]) cube([2 * leg_in, 2, 30 + plate_t + ledge_h]);
        translate([-leg_in, ledge_open / 2, plate_t]) cube([2 * leg_in, 2, ledge_h]);
    }
}

if (part == "guard") guard();
else if (part == "plug") plug();
else if (part == "template") octagon([ri, ri], chamfer);
else if (part == "assembled") {
    guard(); color("SteelBlue") plug_installed(); %ghost_fan(); %ghost_tube();
}
else if (part == "section") intersection() {
    union() { guard(); color("SteelBlue") plug_installed(); color("Gray") ghost_tube(); }
    translate([0, -200, -50]) cube([400, 200, 100]);
}
else {
    guard();
    translate([plate + 10, 0, 0]) plug();
}
