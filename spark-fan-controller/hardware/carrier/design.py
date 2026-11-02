"""Spark Fan Carrier: single source of truth for parts and nets.

RP2040-Zero plugs into J1/J2. Its USB 5 V feeds an MT3608 boost to 12 V for a
4-pin PWM fan. GP28 drives the fan PWM line through an open-drain 2N7002
(inverted, fails to full speed), GP29 reads the tach.

Each part: ref -> (lib_id, value, footprint, sch_xy, {pin: net or None}, fields)
None marks an intentionally unconnected pin.
"""

PROJECT = "spark_fan_carrier"
TITLE = "Spark Fan Carrier"
REV = "A"

FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"

# Verify every LCSC number on lcsc.com before ordering.
PARTS = {
    # RP2040-Zero sockets. J1 is the 5V/GND/3V3/GP29/GP28.. row, J2 (GP0..GP8) is mechanical only.
    "J1": ("Connector:Conn_01x09_Socket", "RP2040-Zero L", "Connector_PinSocket_2.54mm:PinSocket_1x09_P2.54mm_Vertical",
           (50.8, 63.5), {"1": "+5V", "2": "GND", "3": "+3V3", "4": "TACH", "5": "PWM_MCU",
                          "6": None, "7": None, "8": None, "9": None}, {}),
    "J2": ("Connector:Conn_01x09_Socket", "RP2040-Zero R", "Connector_PinSocket_2.54mm:PinSocket_1x09_P2.54mm_Vertical",
           (50.8, 101.6), {str(i): None for i in range(1, 10)}, {}),
    # 5 V input
    "F1": ("Device:Polyfuse", "1.5A hold", "Fuse:Fuse_1206_3216Metric",
           (88.9, 50.8), {"1": "+5V", "2": "VIN"}, {"LCSC": "C20802", "MPN": "Ruilon SMD1206P150TF"}),
    "C1": ("Device:C", "22u 25V", "Capacitor_SMD:C_0805_2012Metric",
           (104.14, 55.88), {"1": "VIN", "2": "GND"}, {"LCSC": "C45783"}),
    "C6": ("Device:C", "100n", FP_C0603,
           (114.3, 55.88), {"1": "VIN", "2": "GND"}, {"LCSC": "C14663"}),
    # Boost 5 V -> 12.36 V (Vfb 0.6 V: 0.6 * (1 + 100k/5.1k))
    "L1": ("Device:L", "4.7u", "Inductor_SMD:L_Sunlord_SWPA5040S",
           (129.54, 50.8), {"1": "VIN", "2": "SW"}, {"LCSC": "C48496", "MPN": "Sunlord SWPA5040S4R7MT"}),
    "U1": ("Regulator_Switching:MT3608", "MT3608", "Package_TO_SOT_SMD:SOT-23-6",
           (149.86, 60.96), {"1": "SW", "2": "GND", "3": "FB", "4": "VIN", "5": "VIN", "6": None},
           {"LCSC": "C84817"}),
    "D1": ("Device:D_Schottky", "SS34", "Diode_SMD:D_SMA",
           (175.26, 50.8), {"1": "+12V", "2": "SW"}, {"LCSC": "C8678"}),
    "R1": ("Device:R", "100k", FP_R, (190.5, 60.96), {"1": "+12V", "2": "FB"}, {"LCSC": "C25803"}),
    "R2": ("Device:R", "5.1k", FP_R, (190.5, 76.2), {"1": "FB", "2": "GND"}, {"LCSC": "C23186"}),
    "C2": ("Device:C", "22u 25V", "Capacitor_SMD:C_1206_3216Metric",
           (205.74, 60.96), {"1": "+12V", "2": "GND"}, {"LCSC": "C12891"}),
    "C3": ("Device:C", "22u 25V", "Capacitor_SMD:C_1206_3216Metric",
           (218.44, 60.96), {"1": "+12V", "2": "GND"}, {"LCSC": "C12891"}),
    # 12 V indicator
    "R8": ("Device:R", "4.7k", FP_R, (233.68, 60.96), {"1": "+12V", "2": "LED_A"}, {"LCSC": "C23162"}),
    "D2": ("Device:LED", "red", "LED_SMD:LED_0603_1608Metric",
           (233.68, 76.2), {"1": "GND", "2": "LED_A"}, {"LCSC": "C2286"}),
    # Fan PWM: open drain, inverted. Gate pulldown keeps the FET off (fan at
    # full speed via its internal pull-up) whenever the RP2040 isn't driving.
    "R4": ("Device:R", "100", FP_R, (101.6, 121.92), {"1": "PWM_MCU", "2": "GATE"}, {"LCSC": "C22775"}),
    "R5": ("Device:R", "100k", FP_R, (116.84, 132.08), {"1": "GATE", "2": "GND"}, {"LCSC": "C25803"}),
    "Q1": ("Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23",
           (134.62, 121.92), {"1": "GATE", "2": "GND", "3": "FAN_PWM"}, {"LCSC": "C8545"}),
    # Tach: open collector from the fan through 1k, pulled up to 3V3 at the RP2040, 1n filter.
    "R6": ("Device:R", "10k", FP_R, (162.56, 116.84), {"1": "+3V3", "2": "TACH"}, {"LCSC": "C25804"}),
    "R7": ("Device:R", "1k", FP_R, (177.8, 132.08), {"1": "TACH", "2": "TACH_FAN"}, {"LCSC": "C21190"}),
    "C5": ("Device:C", "1n", FP_C0603, (193.04, 137.16), {"1": "TACH", "2": "GND"}, {"LCSC": "C1588"}),
    "J3": ("Motor:Fan_4pin", "Fan", "Connector:FanPinHeader_1x04_P2.54mm_Vertical",
           (220.98, 124.46), {"1": "GND", "2": "+12V", "3": "TACH_FAN", "4": "FAN_PWM"}, {}),
    # Power flags for ERC
    "#FLG01": ("power:PWR_FLAG", "PWR_FLAG", "", (88.9, 76.2), {"1": "VIN"}, {}),
    "#FLG02": ("power:PWR_FLAG", "PWR_FLAG", "", (101.6, 76.2), {"1": "GND"}, {}),
    "#FLG03": ("power:PWR_FLAG", "PWR_FLAG", "", (114.3, 76.2), {"1": "+5V"}, {}),
    "#FLG04": ("power:PWR_FLAG", "PWR_FLAG", "", (127.0, 76.2), {"1": "+3V3"}, {}),
    "H1": ("Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
           (60.96, 147.32), {}, {}),
    "H2": ("Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
           (71.12, 147.32), {}, {}),
}

NOTES = [
    ((30.48, 30.48), "Spark Fan Carrier rev A: RP2040-Zero + MT3608 5V->12V boost + 4-pin PWM fan\n"
                     "Firmware: fan_pwm/main.py, PWM_PIN=28, TACH_PIN=29, PWM_INVERTED=True"),
    ((30.48, 114.3), "Fan PWM (Intel 4-wire): open drain, inverted.\n"
                     "RP2040 off -> gate pulled low -> fan pin 4 floats high -> full speed"),
]


def nets():
    out = {}
    for ref, (_, _, _, _, pinmap, _) in PARTS.items():
        for pin, net in pinmap.items():
            if net:
                out.setdefault(net, set()).add((ref, pin))
    return out
