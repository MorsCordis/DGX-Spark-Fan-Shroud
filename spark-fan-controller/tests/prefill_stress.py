#!/usr/bin/env python3
"""Prefill-heavy stress through the running vLLM server (power-off repro).

Ramps through prompt sizes (default 16k -> 32k -> 64k -> 128k tokens), keeping
CONC requests in flight per stage. Each prompt is fresh random words, so the
prefix cache can't skip the work, and max_tokens is tiny so the GPU spends its
time in prefill. A sampler reads nvidia-smi every 200 ms and logs the peak
instant power per interval. Every log line is fsync'd, so the file survives a
hard power-off up to the last second or so.

usage: prefill_stress.py LABEL [stage_k ...]    e.g.  prefill_stress.py 2200MHz 16 32 64 128
env:   STOP_C=<C>      stop load at this temperature (default 88)
       FAN_DUTY=<0-255> hold the shroud fan at this duty instead of spark-fan.service
                        (re-asserted every second; forced to 255 on a temperature stop)
"""
import glob
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"
MODEL = "nemotron-3.5-super-vl"
CONC = 4
STAGE_S = 180
LOG_S = 2
STOP_C = float(os.environ.get("STOP_C", 88))
FAN_DUTY = os.environ.get("FAN_DUTY")
WORDS_PER_TOKEN = 1 / 1.1   # measured with /tokenize: ~1.1 tokens per random word

VOCAB = ("amber quartz velvet harbor lantern ridge copper meadow falcon ember river cobalt willow "
         "granite saffron thistle beacon orchard tundra marble cinder juniper canyon zephyr pewter "
         "lagoon hazel prairie obsidian sparrow nectar glacier walnut indigo mesa basalt clover "
         "fjord topaz heron sienna dune birch onyx violet cedar summit coral aspen slate").split()

label = sys.argv[1] if len(sys.argv) > 1 else "run"
stages = [int(k) * 1024 for k in sys.argv[2:]] or [16384, 32768, 65536, 131072]
logf = open(os.path.expanduser(f"~/spark-fan/prefill_{label}.log"), "a", buffering=1)


def log(line):
    print(line, flush=True)
    logf.write(line + "\n")
    logf.flush()
    os.fsync(logf.fileno())


stop = threading.Event()
lock = threading.Lock()
stats = {"done": 0, "errors": 0, "ptok": 0, "last_err": ""}
stage_tokens = [stages[0]]
samp = {"thr": "", "peak_w": 0.0, "w": float("nan"), "mhz": float("nan"), "util": float("nan"), "gpu_c": float("nan")}
stage_peak = {}


def prompt(n_tok):
    rnd = random.Random()
    words = " ".join(rnd.choice(VOCAB) for _ in range(int(n_tok * WORDS_PER_TOKEN)))
    return (f"Request {rnd.getrandbits(64):x}. Below is a list of words.\n\n{words}\n\n"
            "Which word appears most often? Answer with one word.")


def worker():
    while not stop.is_set():
        body = json.dumps({"model": MODEL, "max_tokens": 16, "temperature": 0,
                           "messages": [{"role": "user", "content": prompt(stage_tokens[0])}]}).encode()
        req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=1200) as r:
                usage = json.load(r).get("usage", {})
            with lock:
                stats["done"] += 1
                stats["ptok"] += usage.get("prompt_tokens", 0)
        except Exception as e:
            with lock:
                stats["errors"] += 1
                stats["last_err"] = str(e)[:120]
            time.sleep(2)


def sampler():
    # P = SW power cap, T = SW thermal slowdown, H = HW slowdown (thermal or power brake)
    p = subprocess.Popen(["nvidia-smi", "--query-gpu=power.draw.instant,clocks.gr,utilization.gpu,temperature.gpu,"
                          "clocks_event_reasons.sw_power_cap,clocks_event_reasons.sw_thermal_slowdown,"
                          "clocks_event_reasons.hw_slowdown",
                          "--format=csv,noheader,nounits", "-lms", "200"],
                         stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        if stop.is_set() and samp.get("cool_done"):
            break
        f = [x.strip() for x in line.split(",")]
        try:
            w, mhz, util, c = (float(x) for x in f[:4])
        except ValueError:
            continue
        thr = "".join(k for k, v in zip("PTH", f[4:]) if v == "Active")
        with lock:
            samp.update(w=w, mhz=mhz, util=util, gpu_c=c, peak_w=max(samp["peak_w"], w),
                        thr="".join(sorted(set(samp["thr"] + thr))))
            k = stage_tokens[0]
            stage_peak[k] = max(stage_peak.get(k, 0.0), w)
    p.terminate()


def zones():
    """Every acpitz zone in C, in hwmon order."""
    temps = []
    for dev in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        try:
            if open(dev + "/name").read().strip() == "acpitz":
                temps += [int(open(q).read()) / 1000 for q in sorted(glob.glob(dev + "/temp*_input"))]
        except (OSError, ValueError):
            pass
    return temps


fan_hold = [int(FAN_DUTY)] if FAN_DUTY is not None else None


def fan_holder():
    import serial
    port = serial.Serial(sorted(glob.glob("/dev/ttyACM*"))[0], 115200, timeout=0)
    while fan_hold[0] is not None:
        port.write(f"DUTY {fan_hold[0]}\n".encode())
        port.read(4096)
        time.sleep(1)
    port.write(f"DUTY {round(service_duty() * 255 / 100)}\n".encode())   # hand back to the service


def fan_duty():
    if fan_hold is not None and fan_hold[0] is not None:
        return fan_hold[0] * 100 / 255
    return service_duty()


def service_duty():
    out = subprocess.run(["journalctl", "-u", "spark-fan", "-n", "1", "--no-pager", "-o", "cat"],
                         capture_output=True, text=True).stdout
    m = re.search(r"duty\s+([\d.]+)%", out)
    return float(m.group(1)) if m else 100.0


def row(tag):
    with lock:
        s = dict(samp)
        samp["peak_w"], samp["thr"] = 0.0, ""
        done, err, ptok = stats["done"], stats["errors"], stats["ptok"]
    z = zones()
    c = max(z) if z else float("nan")
    log(f"{time.strftime('%H:%M:%S')} {tag:>6s}  {c:5.1f}  {s['gpu_c']:5.1f}  {s['w']:5.1f}  {s['peak_w']:5.1f}  "
        f"{s['mhz']:5.0f}  {s['util']:4.0f}  {fan_duty():5.1f}  {done:4d}  {err:3d}  {ptok:8d}  {s['thr'] or '-':3s}  "
        + " ".join(f"{t:.1f}" for t in z))
    return max(c, s["gpu_c"])


clock_cap = subprocess.run(["nvidia-smi", "--query-gpu=clocks.max.gr,clocks.gr", "--format=csv,noheader"],
                           capture_output=True, text=True).stdout.strip()
log(f"# prefill stress {label}  {time.strftime('%Y-%m-%d %H:%M:%S')}  stages(tok)={stages}  conc={CONC}  "
    f"stage_s={STAGE_S}  stop_c={STOP_C}  fan_duty={FAN_DUTY or 'service'}  clocks(max,cur)={clock_cap}")
log("time      stage  cpu_C  gpu_C  W_now  W_pk   MHz   util  fan%  done  err  prompt_tok  thr  acpitz_zones")
threading.Thread(target=sampler, daemon=True).start()
if fan_hold is not None:
    threading.Thread(target=fan_holder, daemon=True).start()
for _ in range(CONC):
    threading.Thread(target=worker, daemon=True).start()

hot = False
try:
    for n in stages:
        stage_tokens[0] = n
        t0 = time.monotonic()
        while time.monotonic() - t0 < STAGE_S:
            if row(f"{n // 1024}k") >= STOP_C:
                log(f"STOP: reached {STOP_C} C")
                if fan_hold is not None:
                    fan_hold[0] = 255
                hot = True
                break
            time.sleep(LOG_S)
        if hot:
            break
finally:
    stop.set()
    with lock:
        log(f"# load stopped: {stats['done']} requests, {stats['ptok']} prompt tokens, {stats['errors']} errors"
            + (f" (last: {stats['last_err']})" if stats["errors"] else ""))
        log("# peak instant GPU W per stage: "
            + ", ".join(f"{k // 1024}k={w:.1f}" for k, w in stage_peak.items()))

cool = time.monotonic()
while time.monotonic() - cool < 120:
    row("cool")
    time.sleep(LOG_S)
samp["cool_done"] = True
if fan_hold is not None:
    fan_hold[0] = None
    time.sleep(2)
