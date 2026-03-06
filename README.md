---
title: SAP Warehouse Copilot
emoji: 🤖
colorFrom: green
colorTo: yellow
sdk: static
pinned: true
license: apache-2.0
tags:
  - reachy_mini
  - nvidia
  - sap
  - voice-assistant
  - warehouse
  - nim
  - riva
---

# 🤖 SAP Warehouse Copilot

**Voice-driven SAP inventory assistant for Reachy Mini — powered by NVIDIA NIM + Riva Speech AI**

> The world's first SAP-integrated Reachy Mini app. Ask about stock levels, purchase orders, and maintenance — your robot responds with voice AND expressive body language.

## Architecture

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│  NVIDIA Riva │────▶│  NVIDIA NIM LLM    │────▶│  NVIDIA Riva │
│  ASR (STT)   │     │  + SAP Tool-Calling│     │  TTS         │
└──────────────┘     └────────────────────┘     └──────────────┘
       │                      │                         │
       │               ┌──────▼──────┐                  │
       │               │  SAP OData  │                  │
       │               │  (MM/WM/PM) │                  │
       │               └─────────────┘                  │
       └──────────┬──────────┼──────────────────────────┘
                  ▼          ▼
          ┌──────────────────────────┐
          │     Reachy Mini Robot    │
          │  Head • Antennas • Voice │
          └──────────────────────────┘
```

## NVIDIA Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | NIM — Llama 3.1 70B | Natural language understanding + SAP tool orchestration |
| **ASR** | Riva Speech-to-Text | Real-time speech recognition from robot microphone |
| **TTS** | Riva Text-to-Speech | Natural voice responses through robot speaker |
| **Inference** | OpenAI-compatible API | Function calling for SAP OData queries |

## SAP Integration

The copilot queries SAP data through OData V4-compatible services:

- **Material Master** (MARA/MAKT) — Material descriptions, types, weights, storage locations
- **Stock Overview** (MARD/MMBE) — Unrestricted, reserved, quality, blocked quantities
- **Purchase Orders** (EKKO/EKPO) — Open, overdue, partially delivered POs
- **Plant Maintenance** (IW39) — Work orders by priority and status
- **Warehouse KPIs** — Aggregate health: GREEN / AMBER / RED

> Demo uses mock data. In production, point to your SAP S/4HANA OData endpoints.

## Robot Behaviors

The robot's body language reflects SAP data states:

| SAP State | Robot Behavior |
|-----------|---------------|
| **Healthy stock** | Happy nod + bouncing antennas |
| **Reorder needed** | Concerned side-to-side sway |
| **Critical stock** | Fast head shake + alternating antennas |
| **Out of stock** | Head drops → snaps up urgently |
| **Overdue PO** | Alert shake with red-state antenna flash |
| **Thinking** | Head tilts up-left + antenna wave |
| **Listening** | Head tilt + perked antennas |

## Setup

### 1. Get NVIDIA API Key
Sign up at [build.nvidia.com](https://build.nvidia.com) — new users get 1,000 free inference credits.

### 2. Set Environment Variables
```bash
export NVIDIA_API_KEY="nvapi-your-key-here"

# Optional: Riva Speech AI (for voice I/O)
export RIVA_ASR_FUNCTION_ID="your-asr-function-id"
export RIVA_TTS_FUNCTION_ID="your-tts-function-id"
```

### 3. Install
```bash
pip install -e .
```

### 4. Run
```bash
# Start Reachy Mini daemon
reachy-mini-daemon

# Dashboard available at http://localhost:7860
```

### 5. Try These Queries
- "What's the overall warehouse status?"
- "Check stock for the hydraulic pump"
- "Show me overdue purchase orders"
- "Any critical maintenance orders?"
- "What needs reordering?"
- "Tell me about MAT-1002"

## Production Deployment

To connect to a real SAP S/4HANA system:

1. Replace `sap_mock.py` with real OData client calls
2. Configure SAP OData endpoints:
   ```
   SAP_ODATA_BASE=https://your-sap-host/sap/opu/odata4/sap/
   SAP_CLIENT=100
   SAP_USER=your-user
   SAP_PASSWORD=your-password
   ```
3. The tool definitions in `sap_mock.py` → `SAP_TOOLS` map directly to SAP OData services

## Author

**Amit Kumar Lal** — SAP Technical Expert | Microsoft | NVIDIA AI Enthusiast

Built with NVIDIA NIM, Riva Speech AI, and Reachy Mini SDK.

## License

Apache 2.0
