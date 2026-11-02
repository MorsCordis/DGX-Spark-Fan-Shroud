#!/usr/bin/env python3
"""A/B cooling test: shroud fan off, then full, logging temperatures.

Runs alongside spark-fan.service by re-asserting DUTY every second, then
hands control back to the service's latest duty when finished.
"""
import glob
import re
import subprocess
import time

import serial

PHASES = [("off", 0, 240), ("full", 255, 360)]
SAMPLE_S = 2
ABORT_C = 80.0


def cpu_temp():
    temps = []
    for dev in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if open(dev + "/name").read().strip() != "acpitz":
                continue
            for p in glob.glob(dev + "/temp*_input"):
                temps.append(int(open(p).read()) / 1000.0)
        except (OSError, ValueError):
            pass
    return max(temps) if temps else float("nan")


def gpu():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=3).stdout.strip().split(",")
    try:
        return float(out[0]), float(out[1]), float(out[2])
    except (IndexError, ValueError):
        return float("nan"), float("nan"), float("nan")


def service_duty():
    log = subprocess.run(["journalctl", "-u", "spark-fan", "-n", "1", "--no-pager", "-o", "cat"],
                         capture_output=True, text=True).stdout
    m = re.search(r"duty\s+([\d.]+)%", log)
    return round(float(m.group(1)) * 255 / 100) if m else 255


s = serial.Serial("/dev/ttyACM0", 115200, timeout=0)
print("time      phase  t(s)  cpu_C  gpu_C  gpu_W  gpu_util", flush=True)
aborted = False
try:
    for name, duty, length in PHASES:
        start = time.monotonic()
        next_sample = start
        while (elapsed := time.monotonic() - start) < length:
            s.write(f"DUTY {duty}\n".encode())
            s.read(4096)
            if time.monotonic() >= next_sample:
                c = cpu_temp()
                g, w, u = gpu()
                print(f"{time.strftime('%H:%M:%S')}  {name:5s} {elapsed:5.0f}  "
                      f"{c:5.1f}  {g:5.1f}  {w:5.1f}  {u:4.0f}", flush=True)
                next_sample += SAMPLE_S
                if max(c, g) >= ABORT_C:
                    print("ABORT: temperature limit, going to full", flush=True)
                    aborted = True
                    break
            time.sleep(1)
        if aborted:
            break
finally:
    if aborted:
        s.write(b"DUTY 255\n")
    else:
        d = service_duty()
        s.write(f"DUTY {d}\n".encode())
        print(f"handed back to service at DUTY {d}", flush=True)
