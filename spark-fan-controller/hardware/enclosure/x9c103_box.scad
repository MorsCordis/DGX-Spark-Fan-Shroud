// Spark fan controller box
// Parametric enclosure for the hyudryu DGX-Spark-Fan-Shroud controller:
// RP2040-Zero + X9C103 module + Owltree PC039b USB-C PWM fan controller.
//
// Layout: the three boards sit in a row on corner locating brackets.
//   -X wall: RP2040-Zero USB-C opening (the one cable to the Spark)
//   +X wall: U-notch for the fan lead, open at the top so the plug drops in
//   lid:     friction-fit lip, vent slots over the Owltree boost converter
//   +/-Y:    zip-tie ears for strapping to the shroud leg or base
//
// Check every value marked MEASURE with calipers before printing.
// Units: mm. X runs along the row of boards, Y across, Z up.
// Hold boards in their brackets with a dab of hot glue or foam tape.

/* [Output] */
part = "print"; // [print, base, lid, assembled]

/* [Board footprints: L along X, W along Y] */
rp_L = 23.5;    // RP2040-Zero (Waveshare datasheet)
rp_W = 18.0;
x9_L = 36.0;    // X9C103 module                          MEASURE
x9_W = 20.0;    //                                        MEASURE
ow_L = 52.0;    // Owltree PC039b                         MEASURE
ow_W = 34.0;    //                                        MEASURE
pcb_t = 1.6;    // thickest of the three PCBs             MEASURE

/* [Clearance below each board: pins, solder tails] */
rp_under = 3;   // raise to ~9 if headers point down
x9_under = 3;   //                                        MEASURE
ow_under = 3;   //                                        MEASURE

/* [Tallest part above each board, incl. plugs and jumpers] */
rp_above = 12;  // Dupont housings ~12; ~4 if wires are soldered
x9_above = 12;
ow_above = 14;  // fan plug seated in its header          MEASURE

/* [Spacing] */
board_gap = 8;  // between boards along X, for wiring
side_gap  = 6;  // each side along Y, for wiring
end_gap   = 6;  // Owltree to the +X wall

/* [RP2040-Zero USB-C opening, -X wall] */
usb_w  = 12.5;  // fits a typical USB-C plug overmold
usb_h  = 7.5;
usb_zc = 1.6;   // connector centre above the PCB top     MEASURE
usb_y  = 9.0;   // connector centre from the board's -Y edge

/* [Fan lead notch, +X wall] */
fan_w = 14;
fan_y = 17;     // notch centre from the Owltree's -Y edge MEASURE
fan_z = 4;      // notch floor above the box floor

/* [Optional Owltree USB-C opening, -Y wall (two-cable wiring)] */
ow_usb_cut = false;
ow_usb_x   = 26;  // from the Owltree's -X edge           MEASURE
ow_usb_zc  = 1.6; // connector centre above the PCB top   MEASURE

/* [Lid] */
vents = true;
display_window = false; // over the Owltree's speed display
disp_x = 10;    // window corner from the Owltree's -X/-Y corner MEASURE
disp_y = 8;
disp_w = 20;
disp_h = 10;

/* [Shell] */
wall      = 2.0;
floor_t   = 2.0;
lid_t     = 2.0;
corner_r  = 3.0;
lip_h     = 4.0;  // lid lip depth
lip_t     = 1.6;
lid_fit   = 0.2;  // lid lip clearance per side
board_fit = 0.3;  // board clearance inside its brackets
pad       = 3.0;  // support pad under each board corner
brk_t     = 1.2;  // bracket wall thickness
brk_rise  = 1.5;  // bracket height above the PCB top

/* [Mounting ears] */
ears   = true;
ear_len = 10;
ear_w   = 16;
ear_t   = 3;
slot_l  = 8;
slot_w  = 3.5;

/* [Hidden] */
$fn = 32;
usb_gap = 0.5;  // RP2040 USB edge to the -X wall

inner_L = usb_gap + rp_L + board_gap + x9_L + board_gap + ow_L + end_gap;
inner_W = max(rp_W, x9_W, ow_W) + 2 * side_gap;
inner_H = max(rp_under + rp_above, x9_under + x9_above, ow_under + ow_above) + pcb_t;

outer_L = inner_L + 2 * wall;
outer_W = inner_W + 2 * wall;
base_H  = floor_t + inner_H;

// Board origins: the -X/-Y corner of each PCB, in box coordinates.
function centred_y(W) = wall + (inner_W - W) / 2;

rp_x = wall + usb_gap;
x9_x = rp_x + rp_L + board_gap;
ow_x = x9_x + x9_L + board_gap;
rp_y = centred_y(rp_W);
x9_y = centred_y(x9_W);
ow_y = ow_usb_cut ? wall + usb_gap : centred_y(ow_W);


// ---------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------

module rrect(L, W, h, r) {
    linear_extrude(h) offset(r) offset(-r) square([L, W]);
}

// One corner bracket for a board corner at the origin, board toward +X/+Y.
module corner_bracket(under) {
    h = under + pcb_t + brk_rise;
    o = board_fit + brk_t;
    cube([pad, pad, under]);                          // support pad
    difference() {                                    // L-shaped locator
        translate([-o, -o, 0]) cube([pad + o, pad + o, h]);
        translate([-board_fit, -board_fit, -1]) cube([pad + o, pad + o, h + 2]);
    }
}

module brackets(x, y, L, W, under) {
    for (cx = [0, 1], cy = [0, 1])
        translate([x + cx * L, y + cy * W, floor_t])
            scale([cx == 1 ? -1 : 1, cy == 1 ? -1 : 1, 1])
                corner_bracket(under);
}

// Zip-tie ear protruding toward -Y from a wall at y = 0.
module ear() {
    translate([-ear_w / 2, -ear_len, 0])
        difference() {
            cube([ear_w, ear_len + 0.5, ear_t]);
            translate([(ear_w - slot_l) / 2, (ear_len - slot_w) / 2, -1])
                cube([slot_l, slot_w, ear_t + 2]);
        }
}


// ---------------------------------------------------------------------
// Base
// ---------------------------------------------------------------------

module shell() {
    difference() {
        rrect(outer_L, outer_W, base_H, corner_r);
        translate([wall, wall, floor_t])
            rrect(inner_L, inner_W, base_H, max(corner_r - wall, 0.01));
    }
}

module cutouts() {
    // RP2040-Zero USB-C, -X wall
    usb_z = floor_t + rp_under + pcb_t + usb_zc;
    translate([-1, rp_y + usb_y - usb_w / 2, usb_z - usb_h / 2])
        cube([wall + usb_gap + 1, usb_w, usb_h]);

    // Fan lead U-notch, +X wall, open at the top
    translate([outer_L - wall - 1, ow_y + fan_y - fan_w / 2, floor_t + fan_z])
        cube([wall + 2, fan_w, base_H]);

    // Optional Owltree USB-C, -Y wall
    if (ow_usb_cut) {
        z = floor_t + ow_under + pcb_t + ow_usb_zc;
        translate([ow_x + ow_usb_x - usb_w / 2, -1, z - usb_h / 2])
            cube([usb_w, wall + usb_gap + 1, usb_h]);
    }
}

module base() {
    difference() {
        union() {
            shell();
            brackets(rp_x, rp_y, rp_L, rp_W, rp_under);
            brackets(x9_x, x9_y, x9_L, x9_W, x9_under);
            brackets(ow_x, ow_y, ow_L, ow_W, ow_under);
            if (ears) {
                translate([outer_L / 2, 0, 0]) ear();
                translate([outer_L / 2, outer_W, 0]) mirror([0, 1, 0]) ear();
            }
        }
        cutouts();
    }
}


// ---------------------------------------------------------------------
// Lid (modelled in place on top of the base)
// ---------------------------------------------------------------------

module lid_assembled() {
    r_in = max(corner_r - wall - lid_fit, 0.01);
    lip_L = inner_L - 2 * lid_fit;
    lip_W = inner_W - 2 * lid_fit;

    difference() {
        union() {
            translate([0, 0, base_H]) rrect(outer_L, outer_W, lid_t, corner_r);
            translate([wall + lid_fit, wall + lid_fit, base_H - lip_h])
                difference() {
                    rrect(lip_L, lip_W, lip_h + 0.01, r_in);
                    translate([lip_t, lip_t, -1])
                        rrect(lip_L - 2 * lip_t, lip_W - 2 * lip_t, lip_h + 2,
                              max(r_in - lip_t, 0.01));
                }
        }

        // Keep the fan notch and USB opening clear of the lip
        translate([outer_L - wall - lid_fit - lip_t - 1, ow_y + fan_y - fan_w / 2,
                   base_H - lip_h - 1])
            cube([lip_t + 2, fan_w, lip_h + 1]);
        translate([wall + lid_fit - 1, rp_y + usb_y - usb_w / 2, base_H - lip_h - 1])
            cube([lip_t + 2, usb_w, lip_h + 1]);

        if (vents)
            for (i = [0 : floor((ow_L - 10) / 5)])
                translate([ow_x + 5 + i * 5, ow_y + ow_W * 0.2, base_H - 1])
                    cube([2, ow_W * 0.6, lid_t + 2]);

        if (display_window)
            translate([ow_x + disp_x, ow_y + disp_y, base_H - 1])
                cube([disp_w, disp_h, lid_t + 2]);
    }
}

// Flipped plate-down for printing.
module lid_print() {
    rotate([180, 0, 0]) translate([0, 0, -(base_H + lid_t)]) lid_assembled();
}

// Ghost boards for the assembled preview.
module boards() {
    color("ForestGreen") translate([rp_x, rp_y, floor_t + rp_under]) cube([rp_L, rp_W, pcb_t]);
    color("RoyalBlue")   translate([x9_x, x9_y, floor_t + x9_under]) cube([x9_L, x9_W, pcb_t]);
    color("DimGray")     translate([ow_x, ow_y, floor_t + ow_under]) cube([ow_L, ow_W, pcb_t]);
}


// ---------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------

echo(str("Outer size: ", outer_L, " x ", outer_W, " x ", base_H + lid_t, " mm"));

if (part == "base") {
    base();
} else if (part == "lid") {
    lid_print();
} else if (part == "assembled") {
    base();
    boards();
    color("LightSteelBlue", 0.45) lid_assembled();
} else {
    base();
    translate([0, -(ear_len + 5), 0]) lid_print();
}
