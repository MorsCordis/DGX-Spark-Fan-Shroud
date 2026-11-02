use <../carrier_case.scad>
difference() { union() { base(); lid(); } translate([11.8, -20, -5]) cube([60, 100, 60]); }
color("green") difference() { ghost(); translate([11.8, -20, -5]) cube([60, 100, 60]); }
