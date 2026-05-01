# SSID Streaming Test

This folder contains a standalone test for the direct Pocket Option WebSocket tick streaming approach, which is being evaluated for OTC SNIPER v3.

## Purpose

The test verifies that the `pocketoptionapi` library connects successfully using a provided SSID, and that ticks correctly flow through the backend's `StreamingService` (which includes OTEO enrichment and manipulation detection), and are emitted via a local Socket.IO connection.

## Prerequisites

1. Active `QuFLX-v2` conda environment
2. A valid `.env` file containing your SSIDs:
```
PO_SSID_DEMO=42["auth",{"session":"...","isDemo":1}]
PO_SSID_REAL=42["auth",{"session":"...","isDemo":0}]
```

## Running the Test

Run the script from the context of this package to avoid pathing issues:

```powershell
conda activate QuFLX-v2
cd c:\v3\OTC_SNIPER\ssid_integration_package\
python ssid_streaming_test\scripts\test_streaming.py --duration 60
```

### Options

- `--asset`: Asset to subscribe to (e.g. `EURUSD_otc`) — defaults to `EURUSD_otc`
- `--duration`: How long to collect in seconds — defaults to 90
- `--real`: Use real account instead of demo
- `--verbose`: Show full tick debug payloads

### Data Output

By default, the script isolates its outputs to `ssid_streaming_test/app/data/`.
You can view the collected `.jsonl` files there.
