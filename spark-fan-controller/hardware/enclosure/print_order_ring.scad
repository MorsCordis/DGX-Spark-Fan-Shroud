// Test ring: the top 10 mm of the 156 x 176 fan shroud base (front rim notch, side and rear
// shelves included), to check the box fits before printing the whole base. Print as is.
shroud_dir = "../../../3D Files";
translate([0, 0, -12]) intersection() {
    import(str(shroud_dir, "/Nvidia DGX Spark/DGX Fan Shroud.stl"), convexity = 6);
    translate([-100, 100, 12]) cube([200, 300, 20]);
}
