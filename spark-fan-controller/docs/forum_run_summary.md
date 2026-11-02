**Controlled prefill ramp: 2200 vs 2400 MHz clock cap (no power-off, but 2400 runs much hotter)**

Setup: single DGX Spark, Ubuntu 24.04.5, kernel 7.0.0-1019-nvidia, driver 580.178.04. Nemotron-3.5-Super-VL-120B-A12B-NVFP4 on vLLM, `--max-num-batched-tokens 8192`, `--max-num-seqs 8`, `--gpu-memory-utilization 0.7`. External 120 mm fan under the box (shroud), which was at 98–100% for the whole load.

Load: 4 concurrent requests of fresh random-word prompts (no prefix-cache hits), `max_tokens 16`, so it's almost pure prefill. Four 3-minute stages with prompts of roughly 25k → 50k → 100k → 200k tokens. nvidia-smi `power.draw.instant` sampled every 200 ms; logged every 2 s with the peak of each interval, plus the acpitz zones (all 7 in the 2400 log). Safety stop at 88 °C on the hottest acpitz zone. 10+ min idle before each run.

**2200 MHz** (`nvidia-smi -lgc 300,2200`, clocks sit at 2184 under load)

```
Stage    Hottest acpitz  GPU max  GPU avg W  Peak instant W
~25k     80.7 C          71 C     49.9       74.4
~50k     83.8 C          77 C     53.6       75.6
~100k    85.8 C          77 C     57.1       76.4
~200k    89.0 C          79 C     56.1       78.9
```

The 88 °C stop tripped 175 s into the last stage. Requests already in flight finished during cool-down and pushed it to 90.4 °C acpitz / 81 °C GPU. In total 44 requests and 2.08 M prompt tokens, 0 errors, **no power-off**.

**2400 MHz** (clocks 2372–2379 under load)

```
Stage    Hottest acpitz             GPU max  GPU avg W  Peak instant W
~25k     88.4 C after ~2 min (stop) 76 C     60.9       97.5
```

Hit the 88 °C stop about 2 minutes into the *first* stage (2200 needed ~12 minutes and the largest prompts). The hottest zones were z0 and z2 (88.4 °C) and z5 (87.3 °C), while the GPU sensor read 76 °C. 0 errors, no power-off. Caveat: this run started ~9 °C warmer at the SoC (54.7 vs 45.7 °C) despite the idle gap.

Takeaways:
- +9% clock gave +22% average and **+31% peak instant power** (74 → 97.5 W). The 2400 peaks are well above the 71–80 W spikes reported before the power-offs here. 2200 keeps the peaks in the high 70s even at ~200k-token prompts.
- The GPU sensor reads ~10 °C below the hottest acpitz zones under prefill. The GPU temp alone understates how hot the package is.
- I never let it run past ~88–90 °C acpitz, so this doesn't show *where* it powers off, only that 2200 + extra airflow got through 2 M+ prompt tokens of long-context prefill cleanly, and that 2400 reaches the same temperature ~6x faster. 88 °C was my own conservative stop (I had other work on the box), not a known limit; the thread has boxes running 91–96 °C acpitz without dying.
- Linux can't see the internal fan (no hwmon fan/pwm, no ACPI fan device, nvidia-smi fan N/A), so I can't log what it was doing. acpitz critical trip is 104.8 °C, which would be an orderly shutdown with log lines, not the silent cut people are seeing.

Logs attached (`prefill_2200MHz.log`, `prefill_2400MHz.log`). Columns: time, stage, hottest acpitz °C, GPU °C, GPU W (instant), peak W in the interval, MHz, util %, external fan %, requests done, errors, cumulative prompt tokens, then all acpitz zones. Stage labels say 16k/32k/64k/128k; those were my targets, and the actual prompts came out ~1.5x bigger (see prompt tokens / requests). Happy to share the test script.
