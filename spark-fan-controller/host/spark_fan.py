#!/usr/bin/env python3
"""Load-anticipating fan control for a DGX Spark, with a thermal fallback.

Fan duty each tick is the MAX of two independent demands:

  load boost      GPU utilization / GPU power and CPU utilization. Only the
                  load ABOVE a slowly-adapting baseline counts, mapped through
                  LOAD_CURVE: a new load spins the fan up immediately (before
                  temperatures move). The baseline only catches up while the
                  temperature has levelled off, so the boost fades over a few
                  minutes of steady load and the fan settles to what the
                  temperature actually needs. When load drops, the baseline
                  drops with it, so the next load step gets the full boost.

  thermal demand  Hottest of CPU (hwmon) and GPU (nvidia-smi) temperature,
                  mapped through TEMP_CURVE. This sets the steady-state speed
                  under sustained load.

Safety overrides, in order:
  - any temperature >= TEMP_PANIC_C            -> 100%
  - no temperature readable                    -> 100%
  - load telemetry unreadable                  -> thermal demand only
  - this script dies / USB link lost           -> firmware watchdog, 100%

Talks to the RP2040 firmware over USB serial: "DUTY 0..255", "PING";
the firmware replies BOOT / OK / ERR ... / RPM <n>.

Usage:
  spark_fan.py                 auto-detect the RP2040 serial port
  spark_fan.py --port /dev/ttyACM0
  spark_fan.py --dry-run       no serial; just print what it would do
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import subprocess
import sys
import time

# ---------------------------------------------------------------------
# Tuning
# ---------------------------------------------------------------------

POLL_S = 1.0

# (load fraction 0..1, duty %). Piecewise linear, held flat beyond the ends.
LOAD_CURVE = [(0.00, 20.0), (0.15, 30.0), (0.50, 65.0), (0.80, 90.0), (1.00, 100.0)]

# (temperature C, duty %). Steady-state curve: the box settles where this
# duty removes the heat being made. 100% is reached before TEMP_PANIC_C.
TEMP_CURVE = [(55.0, 20.0), (68.0, 30.0), (76.0, 50.0), (82.0, 75.0), (87.0, 100.0)]

TEMP_PANIC_C = 90.0

# GPU power that counts as "full load". Used only if nvidia-smi reports
# power.draw; otherwise utilization alone drives the load estimate.
GPU_FULL_POWER_W = 100.0

# CPU work makes less heat per % than the GPU on GB10; scale it down.
CPU_WEIGHT = 0.7

# Load smoothing: fast attack, slow release (exponential time constants).
LOAD_ATTACK_S = 1.0
LOAD_RELEASE_S = 60.0

# Load boost fade: the baseline approaches the current load with this time
# constant, but only while the hottest temperature is changing slower than
# TEMP_STABLE_C_PER_MIN (smoothed over TEMP_SLOPE_S).
BOOST_FADE_S = 180.0
TEMP_STABLE_C_PER_MIN = 1.5
TEMP_SLOPE_S = 60.0

# Fan duty may drop at most this fast. Increases are never limited.
DUTY_FALL_PCT_PER_S = 2.0

STATUS_EVERY_S = 10.0

# hwmon sensor names that carry CPU/SoC temperature (same set as the
# hyudryu FanController software).
CPU_HWMON_NAMES = {
    "acpitz", "coretemp", "cpu_thermal", "cpu-thermal", "k10temp",
    "soc_thermal", "soc-thermal", "zenpower",
}

RP2040_USB_VID = 0x2E8A


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def interp(curve, x):
    """Piecewise-linear lookup in a sorted [(x, y), ...] list."""
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    return curve[-1][1]


def ema(prev, new, dt, tau):
    if prev is None or tau <= 0:
        return new
    return prev + (1.0 - math.exp(-dt / tau)) * (new - prev)


def pct_to_byte(pct):
    return max(0, min(255, int(round(pct * 255.0 / 100.0))))


# ---------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------

def find_cpu_temp_inputs():
    inputs = []
    for dev in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            with open(os.path.join(dev, "name")) as f:
                name = f.read().strip().lower()
        except OSError:
            continue
        if name in CPU_HWMON_NAMES:
            inputs.extend(sorted(glob.glob(os.path.join(dev, "temp*_input"))))
    return inputs


def read_cpu_temp(inputs):
    temps = []
    for path in inputs:
        try:
            with open(path) as f:
                value = float(f.read().strip()) / 1000.0
        except (OSError, ValueError):
            continue
        if -20.0 <= value <= 150.0:
            temps.append(value)
    return max(temps) if temps else None


def _num(field):
    try:
        return float(field)
    except ValueError:
        return None  # "[N/A]", "[Not Supported]", ...


def read_gpu():
    """Return (temp_C, util_pct, power_W); any element may be None."""
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,utilization.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None, None, None
    if out.returncode != 0 or not out.stdout.strip():
        return None, None, None
    temps, utils, powers = [], [], []
    for line in out.stdout.strip().splitlines():
        fields = [s.strip() for s in line.split(",")]
        if len(fields) != 3:
            continue
        t, u, p = (_num(s) for s in fields)
        if t is not None:
            temps.append(t)
        if u is not None:
            utils.append(u)
        if p is not None:
            powers.append(p)
    return (max(temps) if temps else None,
            max(utils) if utils else None,
            sum(powers) if powers else None)


class CpuUtil:
    """Whole-system CPU utilization from /proc/stat deltas."""

    def __init__(self):
        self._last = None

    def read(self):
        try:
            with open("/proc/stat") as f:
                fields = [int(x) for x in f.readline().split()[1:]]
        except (OSError, ValueError):
            return None
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)  # idle + iowait
        total = sum(fields)
        last, self._last = self._last, (idle, total)
        if last is None or total <= last[1]:
            return None
        return 100.0 * (1.0 - (idle - last[0]) / (total - last[1]))


# ---------------------------------------------------------------------
# Serial link
# ---------------------------------------------------------------------

class Link:
    """Sends DUTY/PING to the RP2040; reconnects if the port goes away."""

    def __init__(self, port):
        import serial  # pyserial
        self._serial_mod = serial
        self.port = port
        self.ser = None
        self.rpm = None
        self.last_duty = None
        self._buf = b""

    def _open(self):
        port = self.port or autodetect_port()
        if port is None:
            return False
        try:
            self.ser = self._serial_mod.Serial(port, 115200, timeout=0)
        except self._serial_mod.SerialException:
            self.ser = None
            return False
        self.last_duty = None  # resend on a fresh connection
        print(f"connected to {port}", flush=True)
        return True

    def send(self, duty_byte):
        if self.ser is None and not self._open():
            return
        try:
            if duty_byte != self.last_duty:
                self.ser.write(f"DUTY {duty_byte}\n".encode())
                self.last_duty = duty_byte
            else:
                self.ser.write(b"PING\n")
            self._read()
        except (OSError, self._serial_mod.SerialException):
            print("serial link lost; retrying", flush=True)
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def _read(self):
        self._buf += self.ser.read(512)
        while b"\n" in self._buf:
            line, _, self._buf = self._buf.partition(b"\n")
            s = line.decode("ascii", "ignore").strip()
            if s.startswith("RPM"):
                try:
                    self.rpm = int(s.split()[1])
                except (IndexError, ValueError):
                    pass
            elif s == "BOOT":
                self.last_duty = None  # firmware restarted at 100%; resend
            elif s.startswith("ERR"):
                print(f"firmware: {s}", flush=True)


def autodetect_port():
    try:
        from serial.tools import list_ports
    except ImportError:
        return None
    for p in list_ports.comports():
        if p.vid == RP2040_USB_VID:
            return p.device
    return None


# ---------------------------------------------------------------------
# Control loop
# ---------------------------------------------------------------------

class Controller:
    def __init__(self):
        self.load = None
        self.baseline = 0.0
        self.hot_s = None
        self.slope = 0.0  # C/min, smoothed
        self.duty = None
        self.last_t = None

    def step(self, now, cpu_temp, gpu_temp, gpu_util, gpu_power, cpu_util):
        dt = POLL_S if self.last_t is None else max(0.0, now - self.last_t)
        self.last_t = now

        temps = [t for t in (cpu_temp, gpu_temp) if t is not None]
        hot = max(temps) if temps else None

        # Instantaneous load estimate, 0..1. None if no load telemetry at all.
        parts = []
        if gpu_util is not None:
            parts.append(gpu_util / 100.0)
        if gpu_power is not None:
            parts.append(gpu_power / GPU_FULL_POWER_W)
        if cpu_util is not None:
            parts.append(CPU_WEIGHT * cpu_util / 100.0)
        raw_load = min(1.0, max(parts)) if parts else None

        if raw_load is not None:
            tau = LOAD_ATTACK_S if (self.load is None or raw_load > self.load) else LOAD_RELEASE_S
            self.load = ema(self.load, raw_load, dt, tau)

        if hot is not None:
            prev, self.hot_s = self.hot_s, ema(self.hot_s, hot, dt, TEMP_SLOPE_S / 4)
            if prev is not None and dt > 0:
                inst = (self.hot_s - prev) * 60.0 / dt
                self.slope = ema(self.slope, inst, dt, TEMP_SLOPE_S)

        boost = 0.0
        if raw_load is not None:
            if self.load <= self.baseline:
                self.baseline = self.load
            elif hot is not None and self.slope < TEMP_STABLE_C_PER_MIN:
                self.baseline = ema(self.baseline, self.load, dt, BOOST_FADE_S)
            boost = self.load - self.baseline

        load_pct = interp(LOAD_CURVE, boost) if raw_load is not None else 0.0
        temp_pct = interp(TEMP_CURVE, self.hot_s) if hot is not None else 100.0

        if hot is None:
            target, why = 100.0, "no-temp"
        elif hot >= TEMP_PANIC_C:
            target, why = 100.0, "panic"
        elif raw_load is None:
            target, why = temp_pct, "thermal-only"
        elif temp_pct > load_pct:
            target, why = temp_pct, "thermal"
        else:
            target, why = load_pct, "load"

        # Rise instantly, fall at a limited rate.
        if self.duty is None or target >= self.duty:
            self.duty = target
        else:
            self.duty = max(target, self.duty - DUTY_FALL_PCT_PER_S * dt)

        return self.duty, why, hot, raw_load, load_pct, temp_pct, boost, self.slope


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", help="serial device (default: auto-detect RP2040)")
    ap.add_argument("--dry-run", action="store_true", help="no serial output")
    args = ap.parse_args()

    link = None if args.dry_run else Link(args.port)
    cpu_inputs = find_cpu_temp_inputs()
    if not cpu_inputs:
        print("warning: no CPU hwmon temperature sensors found", flush=True)
    cpu_util = CpuUtil()
    ctl = Controller()
    last_status = 0.0

    while True:
        started = time.monotonic()
        try:
            gpu_temp, gpu_util, gpu_power = read_gpu()
            duty, why, hot, raw_load, load_pct, temp_pct, boost, slope = ctl.step(
                started, read_cpu_temp(cpu_inputs), gpu_temp,
                gpu_util, gpu_power, cpu_util.read(),
            )
        except Exception as exc:  # never leave the fan low on a bug
            print(f"control error: {exc!r}; forcing 100%", flush=True)
            duty, why, hot, raw_load, load_pct, temp_pct = 100.0, "error", None, None, 0.0, 100.0
            boost, slope = 0.0, 0.0

        if link is not None:
            link.send(pct_to_byte(duty))

        if args.dry_run or started - last_status >= STATUS_EVERY_S:
            last_status = started
            rpm = link.rpm if link is not None else None
            print(
                f"duty {duty:5.1f}% [{why:12s}] "
                f"load {('-' if raw_load is None else f'{raw_load:4.2f}')} boost {boost:4.2f} -> {load_pct:5.1f}%  "
                f"temp {('-' if hot is None else f'{hot:5.1f}C')} {slope:+5.1f}C/min -> {temp_pct:5.1f}%  "
                f"rpm {('-' if rpm is None else rpm)}",
                flush=True,
            )

        time.sleep(max(0.0, POLL_S - (time.monotonic() - started)))


if __name__ == "__main__":
    sys.exit(main())
