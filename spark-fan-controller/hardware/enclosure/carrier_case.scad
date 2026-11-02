// Spark Fan Carrier enclosure (FDM, no supports needed)
//
// Coordinates follow the KiCad board: x across (0..24), y along (0 = USB end .. 50 = fan end),
// z up from the case floor's underside. Values marked MEASURE come from datasheets/drawings;
// check them against your parts before printing.
//
// Light pipes: pipes = "bivar" takes Bivar PLPC2 press-fit pipes from the top of the lid
// (PLPC2-3MM over the Zero's RGB LED, PLPC2-500 over the 12 V LED); the guide tubes shroud
// any gap down to the LED. pipes = "filament" takes clear 1.75 mm filament instead: push it in,
// trim flush, sand the end.
//
// Board retention (fix = "clamp"): pegs on the standoffs go through H1/H2 and posts on the
// lid clamp the board down, so no screws are needed. fix = "screw" gives M2.5 self-tap pilots.

part = "print";          // "print" (base + lid side by side), "base", "lid", "assembled"

/* [Board] */
pcb = [24, 50];
pcb_t = 1.6;
hole_xy = [[3, 47], [21, 47]];     // M2.5 mounting holes H1, H2
standoff_h = 3.0;                   // board underside above floor (clears THT pin tails)
fix = "clamp";                      // "clamp" (pegs + lid posts) or "screw"
peg_d = 2.3;                        // H1/H2 are 2.7 mm

/* [RP2040-Zero stack] */
socket_h = 8.5;                     // female header body height          MEASURE
spacer_h = 2.5;                     // male header plastic spacer         MEASURE
zero_t = 1.0;
usb_c = [12.0, 9.0, 3.3];           // board x of USB-C centre, receptacle width, height MEASURE
usb_open = [13.0, 7.5];             // opening in the end wall for an overmolded plug
rgb_xy = [11.8, 15.8];              // Zero's WS2812 LED (board coords)   MEASURE
rgb_h = 0.9;
buttons_xy = [[7.3, 16.3], [16.9, 16.3]];   // BOOT, RESET                MEASURE
button_hole = 2.0;

/* [Carrier LED] */
led_xy = [3.2, 39.8];               // D2 12 V indicator
led_h = 0.8;

/* [Case] */
wall = 2.0;
floor_t = 1.6;
lid_t = 1.6;
gap = 0.4;                          // board-to-wall clearance
head = 1.2;                         // headroom above the USB-C receptacle
lip_h = 2.5;                        // lid lip depth
lip_t = 1.2;
fit = 0.15;                         // lid lip clearance (friction fit)
pipes = "bivar";                    // "bivar" (PLPC2) or "filament"
pipe_bore = pipes == "bivar" ? 2.0 : 1.85;
pipe_od = 4.0;
pipe_gap = 0.8;                     // pipe end above the LED
fan_slot = [11, 9];                 // fan cable slot in the fan-end wall: width, height
ears = true;
ear_hole = 3.4;
$fn = 40;

// Derived heights
board_z = floor_t + standoff_h;
zero_top = board_z + pcb_t + socket_h + spacer_h + zero_t;
inner_top = zero_top + usb_c[2] + head;            // underside of the lid plate
in_x0 = -gap; in_x1 = pcb[0] + gap;
in_y0 = -gap; in_y1 = pcb[1] + gap;
out = [in_x1 - in_x0 + 2 * wall, in_y1 - in_y0 + 2 * wall];
echo(str("outer size ", out[0], " x ", out[1], " x ", inner_top + lid_t, " mm"));

module rounded_box(size, h, r = 2) {
    linear_extrude(h) offset(r) offset(-r) square(size);
}

module outer_shape(h) {
    translate([in_x0 - wall, in_y0 - wall, 0]) rounded_box(out, h);
}

module inner_shape(h, shrink = 0) {
    translate([in_x0 + shrink, in_y0 + shrink, 0])
        rounded_box([in_x1 - in_x0 - 2 * shrink, in_y1 - in_y0 - 2 * shrink], h, 1);
}

module base() {
    difference() {
        union() {
            difference() {
                outer_shape(inner_top);
                translate([0, 0, floor_t]) inner_shape(inner_top);
            }
            // M2.5 standoffs
            for (p = hole_xy) translate([p[0], p[1], 0]) cylinder(d = 5.5, h = board_z);
            if (fix == "clamp") for (p = hole_xy)
                translate([p[0], p[1], 0]) cylinder(d = peg_d, h = board_z + pcb_t - 0.2);
            // side ledges under the USB end of the board
            for (x = [in_x0, pcb[0] - 0.6]) translate([x, 0, 0]) cube([1.0 + gap, 22, board_z]);
            if (ears) for (s = [0, 1])
                translate([pcb[0] / 2, pcb[1] / 2, 0]) mirror([s, 0, 0]) ear();
        }
        if (fix == "screw")
            for (p = hole_xy) translate([p[0], p[1], 1.2]) cylinder(d = 2.2, h = board_z);   // self-tap M2.5
        // USB-C opening, centred on the receptacle
        translate([usb_c[0] - usb_open[0] / 2, in_y0 - wall - 1, zero_top + usb_c[2] / 2 - usb_open[1] / 2])
            cube([usb_open[0], wall + 2, usb_open[1]]);
        // fan cable slot, open to the top so the plug can be fitted with the board in place
        translate([pcb[0] / 2 - fan_slot[0] / 2, in_y1 - 1, inner_top - fan_slot[1]])
            cube([fan_slot[0], wall + 2, fan_slot[1] + 1]);
    }
}

module lid() {
    // modelled in place (plate on top of the walls), flipped for printing in "print"
    difference() {
        union() {
            translate([0, 0, inner_top]) outer_shape(lid_t);
            translate([0, 0, inner_top - lip_h]) difference() {
                inner_shape(lip_h, fit);
                translate([0, 0, -1]) inner_shape(lip_h + 2, fit + lip_t);
            }
            // fill the fan slot's top so the lid closes it to the cable size
            translate([pcb[0] / 2 - fan_slot[0] / 2 + fit, in_y1 - fit, inner_top - 2])
                cube([fan_slot[0] - 2 * fit, wall + fit, 2]);
            // light pipe guides
            pipe(led_xy, board_z + pcb_t + led_h + pipe_gap);
            pipe(rgb_xy, zero_top + rgb_h + pipe_gap);
            // posts that clamp the board onto the standoffs
            if (fix == "clamp") for (p = hole_xy) translate([p[0], p[1], board_z + pcb_t])
                cylinder(d = 4.4, h = inner_top - board_z - pcb_t);
        }
        for (p = [led_xy, rgb_xy]) translate([p[0], p[1], 0]) cylinder(d = pipe_bore, h = 100);
        // Bivar's recommended hole: 2.0 mm through, 60 deg countersink 0.2 mm deep at the top
        if (pipes == "bivar") for (p = [led_xy, rgb_xy])
            translate([p[0], p[1], inner_top + lid_t - 0.2]) cylinder(d1 = 2.0, d2 = 2.0 + 2 * 0.2 * tan(30) * 2, h = 0.21);
        for (p = buttons_xy) translate([p[0], p[1], inner_top - 1]) cylinder(d = button_hole, h = lid_t + 2);
        // the lip must clear the USB opening and fan slot walls
        translate([usb_c[0] - usb_open[0] / 2 - 1, in_y0 - 1, inner_top - lip_h - 1]) cube([usb_open[0] + 2, lip_t + 2, lip_h + 1]);
        translate([pcb[0] / 2 - fan_slot[0] / 2, in_y1 - lip_t - 1, inner_top - lip_h - 1]) cube([fan_slot[0], lip_t + 2, lip_h - 1]);
        // labels
        translate([pcb[0] / 2, 30, inner_top + lid_t - 0.4]) linear_extrude(1)
            text("SPARK FAN", size = 3.2, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
        translate([led_xy[0] + 3.2, led_xy[1], inner_top + lid_t - 0.4]) linear_extrude(1)
            text("12V", size = 2.4, valign = "center");
    }
}

// Mounting ear on the -x side, positioned relative to the board centre.
module ear() {
    edge = in_x0 - wall - pcb[0] / 2;
    difference() {
        hull() {
            translate([edge, -6, 0]) cube([1, 12, 2.5]);
            translate([edge - 5, 0, 0]) cylinder(d = 9, h = 2.5);
        }
        translate([edge - 5, 0, -1]) cylinder(d = ear_hole, h = 5);
    }
}

module pipe(xy, bottom_z) {
    translate([xy[0], xy[1], bottom_z]) cylinder(d = pipe_od, h = inner_top - bottom_z + 0.01);
}

module ghost() {
    translate([0, 0, board_z]) cube([pcb[0], pcb[1], pcb_t]);                    // carrier
    for (x = [3, 18.6]) translate([x + 0.1, 0.3, board_z + pcb_t]) cube([2.3, 23, socket_h]); // sockets
    translate([3, 0, zero_top - zero_t]) cube([18, 23.5, zero_t]);                  // Zero
    translate([usb_c[0] - usb_c[1] / 2, 0, zero_top]) cube([usb_c[1], 7.4, usb_c[2]]);
    translate([rgb_xy[0] - 1, rgb_xy[1] - 1, zero_top]) cube([2, 2, rgb_h]);
    translate([2.4, 39.4, board_z + pcb_t]) cube([1.6, 0.8, led_h]);               // D2
    translate([6.4, 42.3, board_z + pcb_t]) cube([11.2, 6, 11]);                    // fan header + plug
}

module ghost_boards() { %ghost(); }

if (part == "base") base();
else if (part == "lid") translate([0, 0, inner_top + lid_t]) mirror([0, 0, 1]) lid();
else if (part == "assembled") { base(); lid(); ghost_boards(); }
else {
    base();
    translate([out[0] + (ears ? 22 : 8), 0, inner_top + lid_t]) mirror([0, 0, 1]) lid();
}
