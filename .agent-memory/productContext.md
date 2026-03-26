# Product Context

## Project Purpose
OTC SNIPER (QuFLX v2) is an advanced trading platform built for over-the-counter (OTC) assets, specifically designed to automate, analyze, and optimize trading strategies.

## Problem Statement
The previous monolith legacy application was brittle and tightly coupled. The rebuild creates a robust, modular, and performant platform that separates workspace management from the functional application root, ensuring scalable and reliable trading execution and risk management.

## Intended Users
Professional or algorithmic traders requiring complex risk managed strategies, live stream data integration, and execution via PocketOption.

## Core Functionality
- Live real-time streaming of tick data and signals via a gateway.
- Risk management tracking per session, displaying Live P/L, win rates.
- Multi-chart asset viewing and trading via PocketOption.
- Ghost trading for strategy testing before committing real capital.
- AI Integration (Grok) for trading journals, signal confirmation, and risk advisory.

## Success Metrics
- Zero-downtime streaming and execution.
- Maintain a strict boundary between the data repository, session logic, and the React UI.
- Accurate and fail-fast validation of data models using Pydantic.
