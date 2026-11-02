# Load-boost fan controller (headless)

A small, dependency-light alternative to `software/fancontroller` for boxes that run long
inference jobs. It speaks the same serial protocol as `firmware/main.py`
(`DUTY 0..255`, `PING`), so it works with the stock RP2040 firmware.

**Run one controller or the other, not both:** they would fight over the serial port.

## Why

Under LLM inference, GPU utilization sits at 100% for the whole job. If load drives the fan
directly, the fan stays pinned at full speed for the entire run, even while the box is only
at 60-70 C. This controller uses load only to spin the fan up early, then hands control
back to temperature.

## How it works

Every second, fan duty is the **max** of two demands:

- **Load boost:** GPU utilization, GPU power and CPU utilization, minus a slowly
  adapting baseline, mapped through `LOAD_CURVE`.
  - A new load step spins the fan up immediately, before temperatures move.
  - The baseline only catches up (`BOOST_FADE_S`, 180 s) while the hottest temperature
    is changing slower than `TEMP_STABLE_C_PER_MIN` (1.5 C/min).
  - So the boost holds while the box heats up, then fades once it levels off.
  - When load drops, the baseline drops with it, so the next job gets the full boost again.
- **Temperature:** the hottest CPU hwmon sensor or GPU (`nvidia-smi`), lightly smoothed,
  mapped through `TEMP_CURVE`. This sets the steady-state speed under sustained load.

Safety:

| Condition | Fan |
|---|---|
| Any temperature at or above `TEMP_PANIC_C` (90 C) | 100% |
| No readable temperature | 100% |
| Control-loop exception | 100% |
| Script dies or USB link lost | 100% (firmware watchdog) |

Duty rises instantly and falls at most `DUTY_FALL_PCT_PER_S` (2%/s).

Default steady-state curve:

| Hottest sensor | Fan |
|---|---|
| 55 C | 20% |
| 68 C | 30% |
| 76 C | 50% |
| 82 C | 75% |
| 87 C | 100% |

All tuning constants are at the top of `spark_fan.py`.

## Install

```bash
sudo apt install python3-serial
sudo install -D -m 755 spark_fan.py /opt/spark-fan/spark_fan.py
sudo install -m 644 spark-fan.service /etc/systemd/system/spark-fan.service
sudo systemctl daemon-reload
sudo systemctl enable --now spark-fan
journalctl -u spark-fan -f
```

The service runs as a dynamic user in the `dialout` group. The RP2040 port is
auto-detected by USB vendor ID; pass `--port /dev/ttyACMx` in the unit to pin it.
`python3 spark_fan.py --dry-run` prints decisions without touching the serial port.

The status line every 10 s reads:

```
duty  72.0% [thermal     ] load 0.96 boost 0.03 ->  21.0%  temp  80.9C  +0.1C/min ->  72.0%  rpm 0
```

`rpm` is 0 with the stock X9C103 build (no tach wired).

## Status

Developed on an NVIDIA DGX Spark (GB10, GPU clock capped at 2400 MHz) with a Noctua
NF-F12 iPPC-3000 on the X9C103 + Owltree build.

The original load-feedforward version ran there through long-context vLLM prefill and decode
stress runs. The fading boost is new: so far it has only been checked against a simple thermal
model, and it's now running on that box for real-world validation.
