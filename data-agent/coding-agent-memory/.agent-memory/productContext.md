# Product Context — VPS Data Agent & Autonomous Hermes Intelligence

## Project Purpose
The **Data Agent** (`data-agent`) is a high-availability, persistent VPS-based subsystem designed for continuous OTC market tick data collection, Google Cloud analytics persistence, automated Bayesian prior re-calibration, and autonomous AI supervision via the **xAI API** (Grok models) with real-time **WhatsApp notifications** via **OpenWA**.

## Problem Statement
- Live trading applications like `OTC_SNIPER` require continuous, high-frequency tick data to detect market manipulation, model regime changes, and accurately calibrate the **Bayesian Signal Filter**.
- Running data collection exclusively on a local desktop browser session leads to gaps during session restarts or network interruptions.
- `data-agent` solves this by decoupling tick collection and AI intelligence into a 24/7 background service hosted on a Virtual Private Server (VPS), streaming continuous ticks to GCP BigQuery and alerting traders directly via WhatsApp.

## Intended Users
- Traders and automated execution algorithms using `OTC_SNIPER`.
- Risk managers monitoring OTC volatility, Hurst exponents, and manipulation probabilities remotely via WhatsApp.

## Core Functionality
1. **SSID Tick Ingestion**: Connects to Pocket Option WebSocket endpoints using SSID session tokens to stream ticks continuously.
2. **Google Cloud Data Persistence**: Micro-batches tick streams to Google Cloud Storage (GCS) Parquet archives and streams directly to BigQuery (`otc_sniper_analytics.raw_ticks`), with local SQLite database fallback during offline periods.
3. **Bayesian Prior Calibration**: Periodically analyzes historical trade outcomes and tick patterns to update win/loss prior parameters in `app/data/ghost_trades/stats/bayesian_priors.json`.
4. **Hermes AI Supervisor & xAI API**: Autonomous agent harness powered by xAI API (`grok-2` / `grok-beta`) that evaluates trade signals and market regimes.
5. **WhatsApp Gateway (OpenWA)**: Delivers instant trade signal cards, Bayesian filter updates, and market condition alerts to WhatsApp.
6. **Telemetry & Dashboard**: Serves a light-weight HTTP API (port 8090) consumed by the `DataAgentWidget` in the `OTC_SNIPER` web interface.

## Success Metrics
- 99.9% tick stream uptime on VPS.
- Zero tick loss via resilient local SQLite buffering.
- Seamless GCP BigQuery ingestion and GCS Parquet archiving.
- Automatic atomic updates to `bayesian_priors.json`.
- Sub-second WhatsApp signal notification dispatch.
