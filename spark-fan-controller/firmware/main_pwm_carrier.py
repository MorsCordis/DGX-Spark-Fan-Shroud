# RP2040-Zero MicroPython firmware that drives a standard 4-pin PWM fan
# directly (Intel 4-wire fan spec), for the Spark Fan Carrier board
# (hardware/carrier). The carrier's MT3608 boosts USB 5 V to 12 V for the fan.
#
# Carrier wiring:
#   RP2040 GP28  -> 100R -> 2N7002 gate, 100k gate-to-GND pulldown
#   2N7002 drain -> fan pin 4 (PWM)
#   2N7002 source-> GND
#   RP2040 GP29  -> 1k -> fan pin 3 (tach); 10k pull-up to 3V3 and 1n to GND at GP29
#   Fan pin 2 (+12 V) from the boost, fan pin 1 to GND
#
# The transistor makes pin 4 open-drain and inverts the signal, so
# PWM_INVERTED = True. If the RP2040 loses power, the gate pulldown turns the
# transistor off, the fan's internal pull-up takes pin 4 high, and the fan
# runs at full speed.
#
# Serial protocol (unchanged from the X9C103 firmware):
#   DUTY 0..255
#   PING
# Replies: BOOT, OK, ERR <reason>, and RPM <n> once per second.
#
# DUTY 0   = 0% PWM (minimum fan speed)
# DUTY 255 = 100% PWM (maximum fan speed)
#
# Watchdog:
#   No valid command for WATCHDOG_S seconds forces DUTY 255.

import machine
import select
import sys
import time
from machine import Pin, PWM


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PWM_PIN = 28
TACH_PIN = 29

PWM_FREQ_HZ = 25000
PWM_INVERTED = True

# Standard PC fans pulse the tach line twice per revolution.
TACH_PULSES_PER_REV = 2

# Ignore tach edges closer together than this. PWM switching couples onto
# the tach wire; 2 ms still allows readings up to 15000 RPM.
TACH_MIN_PERIOD_US = 2000

WATCHDOG_S = 5
RPM_PERIOD_MS = 1000


# ---------------------------------------------------------------------
# PWM output
# ---------------------------------------------------------------------

pwm = PWM(Pin(PWM_PIN))
pwm.freq(PWM_FREQ_HZ)


def set_duty_byte(duty):
    """Convert the 0..255 DUTY command to a 16-bit PWM duty cycle."""
    duty = int(duty)

    if duty < 0:
        duty = 0
    elif duty > 255:
        duty = 255

    level = duty * 65535 // 255

    if PWM_INVERTED:
        level = 65535 - level

    pwm.duty_u16(level)


# ---------------------------------------------------------------------
# Tachometer input
# ---------------------------------------------------------------------

tach = Pin(TACH_PIN, Pin.IN)

tach_count = 0
last_tach_us = time.ticks_us()


def on_tach(pin):
    """Count falling tach edges, rejecting edges that arrive too soon."""
    global tach_count, last_tach_us

    now = time.ticks_us()

    if time.ticks_diff(now, last_tach_us) >= TACH_MIN_PERIOD_US:
        tach_count += 1
        last_tach_us = now


tach.irq(trigger=Pin.IRQ_FALLING, handler=on_tach)


def take_rpm(elapsed_ms):
    """Return RPM over the last window and reset the pulse counter."""
    global tach_count

    state = machine.disable_irq()
    count = tach_count
    tach_count = 0
    machine.enable_irq(state)

    if elapsed_ms <= 0:
        return 0

    return count * 60000 // (TACH_PULSES_PER_REV * elapsed_ms)


# ---------------------------------------------------------------------
# Safe startup
# ---------------------------------------------------------------------

# Full cooling until the host begins sending commands.
set_duty_byte(255)

print("BOOT")


# ---------------------------------------------------------------------
# Serial command loop
# ---------------------------------------------------------------------

last_cmd_ms = time.ticks_ms()
last_rpm_ms = time.ticks_ms()
watchdog_active = False
buf = ""

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

while True:
    if poll.poll(0):
        ch = sys.stdin.read(1)

        if ch:
            if ch == "\n" or ch == "\r":
                line = buf.strip()
                buf = ""

                if line.startswith("DUTY"):
                    parts = line.split()

                    if len(parts) == 2:
                        try:
                            duty = int(parts[1])

                            if duty < 0 or duty > 255:
                                print("ERR duty-range")
                            else:
                                set_duty_byte(duty)
                                last_cmd_ms = time.ticks_ms()
                                watchdog_active = False
                                print("OK")

                        except ValueError:
                            print("ERR bad-duty")
                    else:
                        print("ERR bad-duty")

                elif line == "PING":
                    last_cmd_ms = time.ticks_ms()
                    watchdog_active = False
                    print("OK")

                elif line == "":
                    pass

                else:
                    print("ERR unknown")

            else:
                buf += ch

                if len(buf) > 64:
                    buf = ""
                    print("ERR line-too-long")

    now = time.ticks_ms()

    # Loss of communication forces maximum cooling.
    if time.ticks_diff(now, last_cmd_ms) > WATCHDOG_S * 1000:
        if not watchdog_active:
            set_duty_byte(255)
            watchdog_active = True

    elapsed = time.ticks_diff(now, last_rpm_ms)

    if elapsed >= RPM_PERIOD_MS:
        last_rpm_ms = now
        print("RPM", take_rpm(elapsed))

    time.sleep_ms(2)
