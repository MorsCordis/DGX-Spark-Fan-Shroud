// Bolt-on intake guard + filter pocket for a 120 mm fan (FDM, no supports needed)
//
// Stack, from the fan's intake face outward (z grows away from the fan):
//   guard plate  hex grille, held by magnets (or screws) at the fan's four 105 mm holes
//   rim          octagonal pocket that holds the filter sheet
//   retainer     open hex grid with a skirt that slides over the rim (friction fit)
//
// The retainer slides down until it touches the filter, so anything from thin mesh up to
// filter_max thick works. Cut the filter as a square of pocket width with the corners
// clipped (template: part = "template"). If the retainer is loose, lower fit; if it's too
// tight to slide, raise it.
//
// Magnet mounts: "screw_head" drives the fan's own (steel) screws into the intake end of the
// holes and uses their heads as the targets; the heads also sit in recesses that locate the
// guard. "magnet" instead glues a small disc magnet flush into each hole. Either way a disc is sealed inside each corner of the guard (printed fan-face down; pause at
// the height echoed below, drop the magnets in, resume). Polarity: stick each guard magnet
// onto its installed fan magnet, mark the face that's exposed, and seat it marked face up.

part = "print";          // "print", "guard", "retainer", "assembled", "template"

/* [Fan] */
fan = 120;
fan_r = 4;                   // frame corner radius
hole_pitch = 105;            // mounting hole spacing
mount = "screw_head";        // "screw_head", "magnet" or "screw"
head = [7.0, 2.5];           // screw_head: fan screw head diameter, height        MEASURE
head_clr = [0.6, 0.3];       // head recess clearance: diameter, depth
hole_d = 5.2;                // screw mount: clears stock fan screws (~5 mm) and M4
open_r = 56;                 // grille radius over the fan opening

/* [Magnets] */
mag = [6.35, 3.18];          // guard magnet 1/4" x 1/8" (Radial Magnets 8193 or K&J D42-N52)
mag_clr = [0.2, 0.2];        // pocket clearance: diameter, depth
skin = 0.6;                  // plastic between the magnet and the fan
cover = 1.0;                 // plastic over the magnet
boss_d = 9.4;                // corner boss around the pocket

/* [Filter] */
filter_max = 6.5;            // deepest filter the pocket takes (1/4" foam)

/* [Guard] */
plate_t = 3.0;               // grille plate thickness (rib depth)
cell = 10;                   // hex cell across flats
rib = 1.2;
pocket = 113;                // pocket width across flats
chamfer = 92;                // pocket corner clip: x + y <= chamfer (clears screw heads)
rim_t = 1.6;

/* [Retainer] */
ret_t = 1.6;                 // grid thickness
ret_cell = 18;
skirt_t = 1.4;
fit = 0.2;                   // skirt-to-rim clearance
tab = [14, 3];               // pull tabs on two sides: width, reach past the skirt

$fn = 48;

r2 = sqrt(2);
rim_in = [pocket / 2, chamfer];
rim_out = [pocket / 2 + rim_t, chamfer + rim_t * r2];
skirt_in = [rim_out[0] + fit, rim_out[1] + fit * r2];
skirt_out = [skirt_in[0] + skirt_t, skirt_in[1] + skirt_t * r2];
echo(str("added height ", plate_t + filter_max + ret_t, " mm; retainer half-width ",
         skirt_out[0], " (fan half-width ", fan / 2, ")"));
magnetic = mount != "screw";
recess = mount == "screw_head" ? head[1] + head_clr[1] : 0;
mag_z = recess + skin;
boss_t = mag_z + mag[1] + mag_clr[1] + cover;
if (magnetic)
    echo(str("PAUSE before the layer at z = ", mag_z + mag[1] + mag_clr[1], " mm to insert magnets; boss height ", boss_t, " mm"));
echo(str("screw head clearance from skirt ", (hole_pitch - skirt_out[1]) / r2, " mm"));

// Square of half-width o[0] with its corners clipped at x + y = o[1].
module octagon(o) {
    intersection() {
        square(2 * o[0], center = true);
        rotate(45) square(o[1] * r2, center = true);
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

module holes_2d(d) {
    for (x = [-1, 1], y = [-1, 1]) translate([x, y] * hole_pitch / 2) circle(d = d);
}

module guard() {
    difference() {
        union() {
            linear_extrude(plate_t) difference() {
                offset(fan_r) offset(-fan_r) square(fan, center = true);
                grille_2d(cell, rib, open_r);
                if (mount == "screw") holes_2d(hole_d);
            }
            if (magnetic) linear_extrude(boss_t) holes_2d(boss_d);
        }
        if (magnetic) translate([0, 0, mag_z])
            linear_extrude(mag[1] + mag_clr[1]) holes_2d(mag[0] + mag_clr[0]);
        if (recess > 0) translate([0, 0, -1])
            linear_extrude(recess + 1) holes_2d(head[0] + head_clr[0]);
    }
    translate([0, 0, plate_t]) linear_extrude(filter_max) difference() {
        octagon(rim_out);
        octagon(rim_in);
    }
}

// Modelled in place (grid at the outer end), flipped grid-down for printing.
module retainer() {
    z0 = plate_t + filter_max + ret_t;
    translate([0, 0, z0 - ret_t]) linear_extrude(ret_t) difference() {
        union() {
            octagon(skirt_out);
            for (s = [-1, 1]) translate([s * (skirt_out[0] + tab[1] / 2), 0])
                offset(1) offset(-1) square([tab[1] + 2, tab[0]], center = true);
        }
        intersection() {
            octagon([rim_in[0] - 0.5, rim_in[1] - 0.5]);
            hex_holes(ret_cell, rib, skirt_out[0]);
        }
    }
    translate([0, 0, z0 - ret_t - filter_max]) linear_extrude(filter_max) difference() {
        octagon(skirt_out);
        octagon(skirt_in);
    }
}

module ghost_fan() {
    translate([0, 0, -25]) difference() {
        linear_extrude(25) offset(fan_r) offset(-fan_r) square(fan, center = true);
        translate([0, 0, -1]) cylinder(r = 58, h = 27);
    }
}

if (part == "guard") guard();
else if (part == "retainer") translate([0, 0, plate_t + filter_max + ret_t]) mirror([0, 0, 1]) retainer();
else if (part == "assembled") { guard(); color("SteelBlue") retainer(); %ghost_fan(); }
else if (part == "template") octagon(rim_in);
else {
    guard();
    translate([fan + 12, 0, plate_t + filter_max + ret_t]) mirror([0, 0, 1]) retainer();
}
