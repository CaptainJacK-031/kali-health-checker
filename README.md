# Kali Health Checker v0.6

A polished, read-only Linux/Kali system health monitor and diagnostics dashboard.

## v0.6 highlights
- Corrected Overview storage presentation with physical disk capacity and a clearly separated root-filesystem usage summary
- Overview network speed integrated into the existing Live Activity area: current download/upload speed plus total transferred data, without adding a large standalone card
- Network interface labels use Received / Download and Sent / Upload terminology
- Network Drops and Errors are clearly separated and show useful traffic counters instead of unrelated memory information
- CPU page keeps one GPU area below usage, adds a scrollable CPU Threads section, and limits Top CPU Consumers to the top 10
- CPU temperature uses real runtime Linux thermal/hwmon data and reports unavailable when no valid sensor exists
- Memory page includes a compact explanation/recommendation for high filesystem cache; cache clearing is never automatic
- Hardware and Security are combined into one main navigation section
- Security keeps SSH, update visibility, authentication/failure events, firewall status and AppArmor, with manual recommendations where appropriate
- Overview Security Snapshot replaced by a compact Users summary
- Overview health findings include More info actions and a readable finding-details area
- History snapshots are saved at most once every 60 seconds and records older than one hour are automatically removed
- New final Commands tab with an organized, searchable/filterable catalog of read-only Linux information commands related to the information represented throughout the project
- Commands support category navigation, permission badges, favorites and one-click copy-to-clipboard
- Existing diagnostic collectors and APIs remain read-only and collector failures remain isolated

## Install
```bash
cd ~/Downloads
unzip kali-health-checker-v0.6.zip
cd kali-health-checker-v0.6
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x run.sh
./run.sh
```

Then open `http://127.0.0.1:8000`.

## Tests
```bash
source .venv/bin/activate
pytest -q
```

## Optional information tools
```bash
sudo apt update
sudo apt install lm-sensors smartmontools util-linux pciutils usbutils sysstat lshw iw
```
These tools are optional. The application remains usable when individual tools are absent.

## Safety
The application is primarily read-only. It does not automatically install/remove packages or change firewall, service, security or system configuration. The Commands tab only copies commands to the clipboard; it never executes them.


## v0.6 changes
- Overview reorganized around a large CPU utilization-by-core visualization and compact Task-Manager-inspired information hierarchy.
- CPU temperature removed as a standalone Overview/CPU card; when real sensor data exists it is shown as a thin temperature line integrated into the Overview core chart.
- CPU Threads now reports actual runtime thread counts (total/running/sleeping/blocked) in a compact section.
- Disk I/O now shows current read/write speed alongside cumulative read/write totals.
- Storage device sizes are presented in human-readable MB/GB/TB in the normal UI.
- CPU page keeps load average in the freed temperature card space and removes the CPU temperature card.


## v0.9 changes
- Large rolling CPU utilization history chart on Overview with 0–100% scale.
- Overview related system values grouped into a compact System Summary panel when space is limited.
- CPU frequency clearly distinguishes Current and Supported/maximum frequency using runtime data.
- Existing v0.9 functionality preserved.


## v0.9 reliability changes
- Replaced the Overview CPU history canvas with a resilient SVG line/area chart.
- Bootstraps CPU history from the one-hour application history when available.
- Fixed the missing `drawSpark` frontend function that could trigger a false UI error.
- Added a real `/favicon.ico` route and favicon asset.
- API connectivity status is kept separate from UI rendering warnings.
- Read-only diagnostics and existing sections are preserved.
