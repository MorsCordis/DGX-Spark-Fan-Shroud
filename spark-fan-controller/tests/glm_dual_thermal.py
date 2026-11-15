#!/usr/bin/env python3
"""Dual-box thermal load test through GLM 5.3 (TP=2, Spark head + Veriton worker).

Phases: idle baseline -> decode (many concurrent generations) -> prefill
(fresh long prompts, no prefix-cache hits) -> cool-down.  Logs both boxes'
hottest acpitz zone and GPU, plus the Spark shroud fan duty/RPM from
spark-fan.service, every LOG_S seconds.  Aborts the load if either box's
hottest temperature reaches STOP_C.

Runs on the Spark.  The Veriton is sampled over the CX7 link (`ssh veriton`).
"""
import glob
import json
import random
import re
import subprocess
import sys
import threading
import time
import urllib.request

BASE = "http://localhost:8000"
MODEL = "nvidia/GLM-5.3-Flash-FP4-Local"
IDLE_S = 60
DECODE_S, DECODE_WORKERS, DECODE_MAX_TOKENS = 900, 8, 16384
PREFILL_S, PREFILL_WORKERS, PREFILL_WORDS = 480, 4, 30000
COOL_S = 300
LOG_S = 3
# Stop guards.  A single acpitz zone follows whichever core the busiest thread
# is on (90+ C while the other zones sit ~25 C lower, gone 3 s after the load
# stops), so the hottest zone is not bulk heat.  Stop when a box's MEAN zone
# temperature (or its GPU) stays at or above STOP_C for SUSTAIN_S, or
# immediately when any single zone reaches HARD_C (ACPI critical trip 104.8 C).
# Hot-spot excursions >= SPOT_NOTE_C are logged but do not stop the test.
STOP_C = 85.0
SUSTAIN_S = 30
HARD_C = 98.0
SPOT_NOTE_C = 90.0
INTERNAL_FANS = ["/sys/class/hwmon/hwmon0/fan1_input", "/sys/class/hwmon/hwmon1/fan1_input"]

SSH = ["ssh", "-o", "ControlMaster=auto", "-o", "ControlPath=/tmp/glmtherm-%r@%h",
       "-o", "ControlPersist=900", "veriton"]
REMOTE = ("for f in /sys/class/hwmon/hwmon*; do case $(cat $f/name) in acpitz*) "
          "cat $f/temp1_input;; esac; done; echo GPU; nvidia-smi "
          "--query-gpu=temperature.gpu,power.draw,utilization.gpu,clocks.gr "
          "--format=csv,noheader,nounits")

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
WORDS = ("amber basin cobalt delta ember fjord granite harbor island juniper kestrel lagoon "
         "meadow nickel orchid prairie quartz raven summit timber umber valley willow xenon "
         "yarrow zephyr anchor beacon canyon dune estuary falcon glacier heron ivory jasper "
         "kelp lantern marble nectar onyx pebble quiver ridge spruce tundra upland vapor").split()

load_stop = threading.Event()
lock = threading.Lock()
stats = {"done": 0, "errors": 0, "aborted": 0}


def post_stream(body, phase_stop):
    """Stream one request; return 'done' or 'aborted' (closed early on load_stop)."""
    body = dict(body, model=MODEL, stream=True)
    req = urllib.request.Request(BASE + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        for line in r:
            if load_stop.is_set() or phase_stop.is_set():
                return "aborted"
            if line.startswith(b"data: [DONE]"):
                break
    return "done"


def run_workers(n, make_body, phase_stop):
    def worker(i):
        k = i
        while not (phase_stop.is_set() or load_stop.is_set()):
            try:
                res = post_stream(make_body(k), phase_stop)
                with lock:
                    stats[res] += 1
            except Exception as e:  # noqa: BLE001
                with lock:
                    stats["errors"] += 1
                print(f"# request error: {e!r}", flush=True)
                time.sleep(2)
            k += n
    ts = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    for t in ts:
        t.start()
    return ts


def decode_body(k):
    return {"messages": [{"role": "user", "content": PROMPTS[k % len(PROMPTS)]}],
            "max_tokens": DECODE_MAX_TOKENS, "temperature": 0.7}


def prefill_body(k):
    rnd = random.Random(time.time_ns() + k)
    text = " ".join(rnd.choice(WORDS) for _ in range(PREFILL_WORDS))
    return {"messages": [{"role": "user", "content": f"[{time.time_ns()}] {text}\n\nReply OK."}],
            "max_tokens": 16, "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False}}


def acpitz():
    vals = []
    for dev in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if open(dev + "/name").read().strip().startswith("acpitz"):
                vals += [int(open(p).read()) / 1000 for p in glob.glob(dev + "/temp*_input")]
        except (OSError, ValueError):
            pass
    return vals


def gpu_local():
    out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu,"
                          "clocks.gr", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=5).stdout
    return parse_gpu(out)


def parse_gpu(line):
    try:
        return tuple(float(x) for x in line.strip().split(",")[:4])
    except ValueError:
        return (float("nan"),) * 4


def veriton():
    try:
        out = subprocess.run(SSH + [REMOTE], capture_output=True, text=True, timeout=8).stdout
        zones_txt, gpu_txt = out.split("GPU", 1)
        zones = [int(x) / 1000 for x in zones_txt.split()]
        return zones, parse_gpu(gpu_txt)
    except Exception:  # noqa: BLE001
        return [], (float("nan"),) * 4


def fan():
    log = subprocess.run(["journalctl", "-u", "spark-fan", "-n", "1", "--no-pager", "-o", "cat"],
                         capture_output=True, text=True).stdout
    m = re.search(r"duty\s+([\d.]+)%\s+\[(\S+)", log)
    r = re.search(r"rpm\s+(\d+)", log)
    return (float(m.group(1)) if m else float("nan"), m.group(2) if m else "?",
            int(r.group(1)) if r else -1)


def internal_fans():
    out = []
    for p in INTERNAL_FANS:
        try:
            out.append(int(open(p).read()))
        except (OSError, ValueError):
            out.append(-1)
    return out


def gen_tokens():
    try:
        txt = urllib.request.urlopen(BASE + "/metrics", timeout=5).read().decode()
        p = sum(float(m) for m in re.findall(r"^vllm:prompt_tokens_total\{[^}]*\} (\S+)", txt, re.M))
        g = sum(float(m) for m in re.findall(r"^vllm:generation_tokens_total\{[^}]*\} (\S+)", txt, re.M))
        return p, g
    except Exception:  # noqa: BLE001
        return float("nan"), float("nan")


def mx(v):
    return max(v) if v else float("nan")


def mean(v):
    return sum(v) / len(v) if v else float("nan")


HDR = ("time     phase    t(s) | S_mean S_max S_gpu  S_W   S_util S_MHz fan%  fan_why   rpm  | "
       "V_mean V_max V_gpu  V_W   V_util V_MHz | done err | int fans | S_zones / V_zones")
peaks = {}


def sample(phase, t0):
    sz = acpitz()
    sg = gpu_local()
    vz, vg = veriton()
    d, why, rpm = fan()
    ifan = internal_fans()
    s_bulk, v_bulk = max(mean(sz), sg[0]), max(mean(vz), vg[0])
    s_hot, v_hot = mx(sz), mx(vz)
    pk = peaks.setdefault(phase, {"S_mean": 0.0, "S_max": 0.0, "V_mean": 0.0, "V_max": 0.0,
                                  "SW": 0.0, "VW": 0.0, "fan": 0.0, "rpm": 0})
    for key, val in (("S_mean", mean(sz)), ("S_max", s_hot), ("V_mean", mean(vz)), ("V_max", v_hot),
                     ("SW", sg[1]), ("VW", vg[1]), ("fan", d), ("rpm", rpm)):
        if val == val and val > pk[key]:
            pk[key] = val
    with lock:
        done, err = stats["done"] + stats["aborted"], stats["errors"]
    print(f"{time.strftime('%H:%M:%S')} {phase:8s} {time.monotonic() - t0:5.0f} | "
          f"{mean(sz):5.1f}  {mx(sz):5.1f} {sg[0]:4.0f}  {sg[1]:5.1f}  {sg[2]:4.0f}  {sg[3]:5.0f} "
          f"{d:5.1f}  {why:8s} {rpm:5d} | "
          f"{mean(vz):5.1f}  {mx(vz):5.1f} {vg[0]:4.0f}  {vg[1]:5.1f}  {vg[2]:4.0f}  {vg[3]:5.0f} | "
          f"{done:4d} {err:3d} | int {ifan[0]:4d} {ifan[1]:4d} | "
          f"{' '.join(f'{z:.1f}' for z in sz)} / "
          f"{' '.join(f'{z:.1f}' for z in vz)}", flush=True)
    return {"S": (s_bulk, s_hot), "V": (v_bulk, v_hot)}


def phase_run(name, seconds, workers=0, make_body=None):
    phase_stop = threading.Event()
    p0, g0 = gen_tokens()
    if workers:
        run_workers(workers, make_body, phase_stop)
    t0 = time.monotonic()
    above_since = {"S": None, "V": None}
    spot_since = {"S": None, "V": None}
    while time.monotonic() - t0 < seconds:
        hot = sample(name, t0)
        now = time.monotonic()
        stop_reason = None
        for box, (temp, spot) in hot.items():
            if spot == spot and spot >= HARD_C:
                stop_reason = f"{box} zone hit hard limit {spot:.1f} C"
            elif spot == spot and spot >= SPOT_NOTE_C and spot_since[box] is None:
                spot_since[box] = now
                print(f"# hotspot start {box} {spot:.1f} C (bulk {temp:.1f} C)", flush=True)
            elif spot == spot and spot < SPOT_NOTE_C and spot_since[box] is not None:
                print(f"# hotspot end {box} after {now - spot_since[box]:.0f} s", flush=True)
                spot_since[box] = None
            if temp != temp:  # NaN: sensor read failed
                continue
            if temp >= STOP_C:
                if above_since[box] is None:
                    above_since[box] = now
                    print(f"# bulk over {STOP_C} C: {box} {temp:.1f} C (stops if held {SUSTAIN_S} s)", flush=True)
                elif now - above_since[box] >= SUSTAIN_S:
                    stop_reason = f"{box} held >= {STOP_C} C for {now - above_since[box]:.0f} s ({temp:.1f} C)"
            elif above_since[box] is not None:
                print(f"# bulk cleared: {box} back to {temp:.1f} C after "
                      f"{now - above_since[box]:.0f} s", flush=True)
                above_since[box] = None
        if workers and stop_reason:
            print(f"# STOP in {name}: {stop_reason}; aborting load", flush=True)
            load_stop.set()
            break
        time.sleep(LOG_S)
    phase_stop.set()
    p1, g1 = gen_tokens()
    el = time.monotonic() - t0
    print(f"# {name}: {el:.0f} s, prompt tok {p1 - p0:,.0f}, gen tok {g1 - g0:,.0f} "
          f"({(g1 - g0) / el:.1f} gen tok/s), peaks {peaks.get(name)}", flush=True)


def main():
    print(f"# GLM dual-box thermal test {time.strftime('%Y-%m-%d %H:%M:%S %Z')}, stop: mean zone/GPU >= {STOP_C} C held {SUSTAIN_S} s, or any zone {HARD_C} C", flush=True)
    print(HDR, flush=True)
    phase_run("idle", IDLE_S)
    if not load_stop.is_set():
        phase_run("decode", DECODE_S, DECODE_WORKERS, decode_body)
    if not load_stop.is_set():
        phase_run("prefill", PREFILL_S, PREFILL_WORKERS, prefill_body)
    load_stop.set()  # close any in-flight streams
    phase_run("cool", COOL_S)
    print(f"# totals {stats}", flush=True)
    print(f"# peaks {json.dumps(peaks)}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
