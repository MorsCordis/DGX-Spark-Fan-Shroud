// Spark Fan Carrier enclosure, v2 (FDM, no supports needed). v1 is carrier_case_v1.scad.
//
// v1 failures fixed here:
//   - Mirrored text: v1 flipped the lid for printing with mirror([0,0,1]), a reflection, so the
//     printed lid was the mirror image of the design (backwards text, 12 V light pipe moved to
//     the wrong side). The lid is now ROTATED for printing.
//   - Board did not snap in: v1 had loose locating pegs only. Four flex hooks cut into the
//     side walls now snap over the board's long edges (both edges are clear of parts).
//   - Nothing held the lid: two latch tabs on the lid snap into windows in the side walls.
//     To open, press each latch bump in through its window and lift.
//
// Coordinates follow the KiCad board: x across (0..24), y along (0 = USB end .. 50 = fan end),
// z up from the case floor's underside. MEASURE values come from datasheets/drawings.
//
// Light pipes: pipes = "bivar" takes Bivar PLPC2 press-fit pipes from the top of the lid
// (PLPC2-3MM over the Zero's RGB LED, PLPC2-500 over the 12 V LED); pipes = "filament" takes
// clear 1.75 mm filament instead.

part = "print";          // "print" (base + lid), "base", "lid", "assembled", "section"
section_y = 10;          // section: cut plane (10 = a board hook, 25 = the lid latches)

/* [Board] */
pcb = [24, 50];
pcb_t = 1.6;
hole_xy = [[3, 47], [21, 47]];      // M2.5 mounting holes H1, H2
standoff_h = 4.5;                   // board underside above floor; sets the hook length
fix = "snap";                       // "snap" (wall hooks) or "screw" (M2.5 self-tap pilots)
peg_d = 2.4;                        // locating pegs in H1/H2 (holes are 2.7 mm)
lid_posts = true;                   // lid posts press the fan end of the board down

/* [Board hooks] */
hook_y = [10, 36];                  // along both long edges; edges are clear of parts here
hook_w = 6;                         // beam width (y)
hook_t = 0.9;                       // beam thickness (flex direction)
hook_slot = 0.6;                    // cut around the beam
hook_nose = 0.6;                    // overlap onto the board's top face
hook_gap = 0.1;                     // nose underside above the board top
ledge_w = 0.9;                      // edge support ledge under the board, 0.5 mm off the wall

/* [Lid latches] */
latch_y = 25;
latch_w = 8;
latch_t = 1.0;
latch_len = 9;                      // tab length below the lid plate
latch_bump = 0.6;                   // 45 deg lock face, 1.2 mm ramp
latch_slot = 0.6;

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
fit = 0.15;                         // lid lip clearance
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
board_top = board_z + pcb_t;
zero_top = board_top + socket_h + spacer_h + zero_t;
inner_top = zero_top + usb_c[2] + head;            // underside of the lid plate
in_x0 = -gap; in_x1 = pcb[0] + gap;
in_y0 = -gap; in_y1 = pcb[1] + gap;
out = [in_x1 - in_x0 + 2 * wall, in_y1 - in_y0 + 2 * wall];
hook_ramp = 1.4;
beam_top = board_top + hook_gap + 0.4 + hook_ramp;
latch_z = inner_top - latch_len;                    // latch tab tip
// window top: just above the highest point of the bump that reaches into the wall
win_top = latch_z + 0.3 + 1.2 + latch_bump - fit + 0.1;

echo(str("outer size ", out[0], " x ", out[1], " x ", inner_top + lid_t, " mm"));
echo(str("hook beam ", beam_top - floor_t, " mm, strain ~",
         round(1500 * hook_t * hook_nose / pow(beam_top - floor_t, 2)) / 10, " %; latch strain ~",
         round(1500 * latch_t * latch_bump / (latch_len * latch_len)) / 10, " %"));

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

// Everything per long side is built for the x = 0 (left) wall and mirrored about the board
// centre line for the right wall.
module both_sides() {
    children();
    translate([pcb[0], 0, 0]) mirror([1, 0, 0]) children();
}

// Window cut around one board hook (left wall). The beam is what the cuts leave standing.
module hook_cut(y) {
    x_out = in_x0 - wall - 1;
    y0 = y - hook_w / 2 - hook_slot;
    // behind the beam (lets it flex outward) and the slots either side
    translate([x_out, y0, floor_t]) cube([in_x0 - hook_t - x_out, hook_w + 2 * hook_slot, beam_top + hook_slot - floor_t]);
    for (s = [y0, y + hook_w / 2])
        translate([x_out, s, floor_t]) cube([in_x0 + 0.01 - x_out, hook_slot, beam_top + hook_slot - floor_t]);
    // clearance above the beam (the wall above bridges it)
    translate([x_out, y0, beam_top]) cube([in_x0 + 0.01 - x_out, hook_w + 2 * hook_slot, hook_slot]);
}

// Hook nose on the beam's inner face: flat underside over the board, ramp on top.
module hook_nose(y) {
    z0 = board_top + hook_gap;
    translate([0, y + hook_w / 2, 0]) rotate([90, 0, 0]) linear_extrude(hook_w)
        polygon([[in_x0 - 0.01, z0], [hook_nose, z0], [hook_nose, z0 + 0.4],
                 [in_x0 - 0.01, beam_top]]);
}

// Window in the left wall for the lid latch bump.
module latch_window() {
    translate([in_x0 - wall - 1, latch_y - latch_w / 2 - 0.3, latch_z])
        cube([wall + 1.01, latch_w + 0.6, win_top - latch_z]);
}

module base() {
    difference() {
        union() {
            difference() {
                outer_shape(inner_top);
                translate([0, 0, floor_t]) inner_shape(inner_top);
            }
            // standoffs + locating pegs at H1/H2
            for (p = hole_xy) translate([p[0], p[1], 0]) cylinder(d = 5.5, h = board_z);
            if (fix == "snap") for (p = hole_xy)
                translate([p[0], p[1], 0]) cylinder(d = peg_d, h = board_top - 0.2);
            // edge ledges under both long edges, clear of the hook beams
            both_sides() translate([in_x0 + 0.5, 1, 0]) cube([ledge_w, 43, board_z]);
            if (fix == "snap") both_sides() for (y = hook_y) hook_nose(y);
            if (ears) for (s = [0, 1])
                translate([pcb[0] / 2, pcb[1] / 2, 0]) mirror([s, 0, 0]) ear();
        }
        if (fix == "snap") both_sides() for (y = hook_y) hook_cut(y);
        both_sides() latch_window();
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

// Latch tab hanging from the lid plate on the left side, bump pointing out (-x).
module latch_tab() {
    xo = in_x0 + fit;                   // tab outer face
    translate([0, latch_y + latch_w / 2, 0]) rotate([90, 0, 0]) linear_extrude(latch_w)
        polygon([
            [xo, inner_top + 0.01], [xo, latch_z + 0.3 + 1.2 + latch_bump],
            [xo - latch_bump, latch_z + 0.3 + 1.2],          // 45 deg lock face above
            [xo, latch_z + 0.3],                               // ramp below
            [xo, latch_z], [xo + latch_t, latch_z], [xo + latch_t, inner_top + 0.01]
        ]);
}

module lid() {
    // modelled in place (plate on top of the walls); "print" rotates it, never mirrors it
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
            pipe(led_xy, board_top + led_h + pipe_gap);
            pipe(rgb_xy, zero_top + rgb_h + pipe_gap);
            // posts that press the fan end of the board onto the standoffs
            if (lid_posts) for (p = hole_xy) translate([p[0], p[1], board_top])
                cylinder(d = 4.4, h = inner_top - board_top);
        }
        // free the latch tabs from the lip
        both_sides() translate([in_x0 - 1, latch_y - latch_w / 2 - latch_slot, inner_top - lip_h - 1])
            cube([fit + lip_t + 2, latch_w + 2 * latch_slot, lip_h + 1]);
        for (p = [led_xy, rgb_xy]) translate([p[0], p[1], 0]) cylinder(d = pipe_bore, h = 100);
        // Bivar's recommended hole: 2.0 mm through, 60 deg countersink 0.2 mm deep at the top
        if (pipes == "bivar") for (p = [led_xy, rgb_xy])
            translate([p[0], p[1], inner_top + lid_t - 0.2]) cylinder(d1 = 2.0, d2 = 2.0 + 2 * 0.2 * tan(30) * 2, h = 0.21);
        for (p = buttons_xy) translate([p[0], p[1], inner_top - 1]) cylinder(d = button_hole, h = lid_t + 2);
        // the lip must clear the USB opening and fan slot walls
        translate([usb_c[0] - usb_open[0] / 2 - 1, in_y0 - 1, inner_top - lip_h - 1]) cube([usb_open[0] + 2, lip_t + 2, lip_h + 1]);
        translate([pcb[0] / 2 - fan_slot[0] / 2, in_y1 - lip_t - 1, inner_top - lip_h - 1]) cube([fan_slot[0], lip_t + 2, lip_h - 1]);
        // labels, engraved in the top face
        translate([pcb[0] / 2, 30, inner_top + lid_t - 0.4]) linear_extrude(1)
            text("SPARK FAN", size = 3.2, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
        translate([led_xy[0] + 3.2, led_xy[1], inner_top + lid_t - 0.4]) linear_extrude(1)
            text("12V", size = 2.4, valign = "center");
    }
    both_sides() latch_tab();
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
    for (x = [3, 18.6]) translate([x + 0.1, 0.3, board_top]) cube([2.3, 23, socket_h]); // sockets
    translate([3, 0, zero_top - zero_t]) cube([18, 23.5, zero_t]);                  // Zero
    translate([usb_c[0] - usb_c[1] / 2, 0, zero_top]) cube([usb_c[1], 7.4, usb_c[2]]);
    translate([rgb_xy[0] - 1, rgb_xy[1] - 1, zero_top]) cube([2, 2, rgb_h]);
    translate([2.4, 39.4, board_top]) cube([1.6, 0.8, led_h]);                     // D2
    translate([6.4, 42.3, board_top]) cube([11.2, 6, 11]);                          // fan header + plug
}

// The lid as printed: rotated 180 deg about y (plate on the bed), never mirrored.
module lid_printed() {
    translate([in_x1 + wall, 0, inner_top + lid_t]) rotate([0, 180, 0]) lid();
}

if (part == "base") base();
else if (part == "lid") lid_printed();
else if (part == "assembled") { base(); color("SteelBlue", 0.9) lid(); %ghost(); }
else if (part == "section") intersection() {
    union() { base(); color("SteelBlue") lid(); color("Green") ghost(); }
    translate([-20, section_y, -1]) cube([70, 80, 60]);
}
else {
    base();
    translate([out[0] + (ears ? 22 : 8), 0, 0]) lid_printed();
}
