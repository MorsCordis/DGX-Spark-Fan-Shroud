**How I capped the GB10 GPU clock (persistent across reboots)**

GB10 doesn't expose a power limit (`nvidia-smi -pl` / `power.limit` shows N/A), but locked graphics clocks work. Max graphics clock is 3003 MHz (default applications clock reads 2418 MHz); I lock it to 300–2200 MHz. Driver 580.178.04.

Try it once (lasts until reboot):

```bash
sudo nvidia-smi -pm 1               # persistence mode, so the setting sticks while no process holds the GPU
sudo nvidia-smi -lgc 300,2200       # lock graphics clock range: min,max in MHz
nvidia-smi --query-gpu=clocks.gr,clocks.max.gr --format=csv   # under load clocks.gr should sit ~2184-2190
sudo nvidia-smi -rgc                # undo: reset to default clocks
```

Make it permanent with a oneshot systemd unit, `/etc/systemd/system/gb10-clock-cap.service`:

```ini
[Unit]
Description=Cap the GB10 GPU clock at 2200 MHz
After=nvidia-persistenced.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/nvidia-smi -pm 1
ExecStart=/usr/bin/nvidia-smi -lgc 300,2200
ExecStop=/usr/bin/nvidia-smi -rgc

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gb10-clock-cap
```

`systemctl stop gb10-clock-cap` restores stock clocks. To try another cap, edit the `-lgc` line and `systemctl restart` the unit. It runs fine alongside a live vLLM server; no restart needed.

Notes:
- The idea is to clip the short power spikes during long prefills, which is where the silent power-offs happen. It does not stop the GPU running at 96% util, it just runs slower clocks. Prefill throughput drops roughly in proportion.
- With the cap on since Oct 17, the box has run all day under agent/repo workloads without a power-off. That's not proof; I'm now running a controlled prefill ramp (25k → 200k token prompts, 4 concurrent, 2 s log rows with peak nvidia-smi instant power sampled every 200 ms, plus the hottest acpitz zone) at 2200 and then at 2400/2600, and will post the logs.
- I've also added an external 120 mm fan (Noctua industrialPPC-3000) under the box, driven from GPU util/power with a temperature fallback, so it's at full speed before the prefill heat arrives. Results will show both effects together, so I'll be clear about which is which.
