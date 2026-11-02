#!/usr/bin/env python3
"""Thermal stress through the running vLLM server; logs temps and fan duty.

Keeps WORKERS hard generation requests in flight against the local
OpenAI-compatible endpoint for DURATION_S, while spark-fan.service keeps
control of the fan. Stops early if any temperature reaches STOP_C.
"""
import glob
import json
import re
import subprocess
import threading
import time
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"
MODEL = "nemotron-3.5-super-vl"
WORKERS = 24
DURATION_S = 900
LOG_S = 5
STOP_C = 88.0

PROMPTS = [
    "Prove that there are infinitely many primes of the form 4k+3, then generalize the argument as far as it goes and explain exactly where it breaks for 4k+1.",
    "Write a complete, well-commented Python implementation of a B-tree of order t with insert, delete and range search, then walk through deleting a key that forces a merge.",
    "Derive the S-parameters of a lossless quarter-wave transformer matching 50 ohms to 200 ohms, then compute its fractional bandwidth for a 1.5:1 VSWR limit.",
    "Solve the 8-queens problem by reasoning, list all 92 solutions in a compact notation, and explain how to reduce them to the 12 fundamental ones.",
    "Design a lock-free multi-producer multi-consumer ring buffer in C11 atomics. Explain every memory ordering choice and the ABA risks.",
    "Compute, step by step, the eigenvalues and eigenvectors of the 4x4 matrix [[4,1,0,0],[1,4,1,0],[0,1,4,1],[0,0,1,4]] and verify them.",
    "Explain and implement in Rust a persistent red-black tree with structural sharing, including the delete fix-up cases.",
    "Plan a 3-stage microwave LNA at 10 GHz: choose topology, bias points, stability approach and matching networks, and estimate the cascaded noise figure.",
]

stop = threading.Event()
lock = threading.Lock()
stats = {"done": 0, "errors": 0, "tokens": 0}


def worker(i):
    n = i
    while not stop.is_set():
        body = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPTS[n % len(PROMPTS)]}],
            "max_tokens": 4096,
            "temperature": 0.7,
        }).encode()
        n += 1
        req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                usage = json.load(r).get("usage", {})
            with lock:
                stats["done"] += 1
                stats["tokens"] += usage.get("completion_tokens", 0)
        except Exception:
            with lock:
                stats["errors"] += 1
            time.sleep(2)


def cpu_temp():
    temps = []
    for dev in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if open(dev + "/name").read().strip() == "acpitz":
                temps += [int(open(p).read()) / 1000 for p in glob.glob(dev + "/temp*_input")]
        except (OSError, ValueError):
            pass
    return max(temps) if temps else float("nan")


def gpu():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=3).stdout.split(",")
    try:
        return tuple(float(x) for x in out[:3])
    except ValueError:
        return (float("nan"),) * 3


def fan_duty():
    log = subprocess.run(["journalctl", "-u", "spark-fan", "-n", "1", "--no-pager", "-o", "cat"],
                         capture_output=True, text=True).stdout
    m = re.search(r"duty\s+([\d.]+)%\s+\[(\S+)", log)
    return (float(m.group(1)), m.group(2)) if m else (float("nan"), "?")


threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(WORKERS)]
start = time.monotonic()
print("time      t(s)  cpu_C  gpu_C  gpu_W  util  fan%  fan_why   done  tok", flush=True)
for t in threads:
    t.start()

try:
    while (el := time.monotonic() - start) < DURATION_S:
        c = cpu_temp()
        g, w, u = gpu()
        d, why = fan_duty()
        with lock:
            done, tok = stats["done"], stats["tokens"]
        print(f"{time.strftime('%H:%M:%S')} {el:5.0f}  {c:5.1f}  {g:5.1f}  {w:5.1f}  {u:4.0f}  "
              f"{d:5.1f}  {why:8s} {done:5d} {tok:6d}", flush=True)
        if max(c, g) >= STOP_C:
            print(f"STOP: reached {max(c, g):.1f} C", flush=True)
            break
        time.sleep(LOG_S)
finally:
    stop.set()
    print(f"load stopped; {stats['done']} requests, {stats['tokens']} tokens, "
          f"{stats['errors']} errors", flush=True)

# Cool-down: keep logging for 3 minutes (requests already in flight finish on their own).
cool = time.monotonic()
while time.monotonic() - cool < 180:
    c = cpu_temp()
    g, w, u = gpu()
    d, why = fan_duty()
    print(f"{time.strftime('%H:%M:%S')} cool  {c:5.1f}  {g:5.1f}  {w:5.1f}  {u:4.0f}  {d:5.1f}  {why}", flush=True)
    time.sleep(LOG_S)
