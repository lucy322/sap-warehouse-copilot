"""
SAP Warehouse Copilot — Standalone web app for Hugging Face Spaces.

Runs the FastAPI dashboard with NVIDIA NIM brain + SAP mock data.
No Reachy Mini robot required — pure web experience.
"""

import logging
import pathlib

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

from sap_warehouse_copilot.nvidia_brain import NVIDIABrain

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="SAP Warehouse Copilot")

# Global state
brain = NVIDIABrain()
shared_state = {
    "state": "idle",
    "last_query": "",
    "last_response": "Hello! I'm your SAP Warehouse Copilot, powered by NVIDIA NIM. Ask me about stock levels, purchase orders, or maintenance. I'm ready!",
    "last_metadata": {},
    "conversation_log": [
        {"role": "assistant", "content": "Hello! I'm your SAP Warehouse Copilot, powered by NVIDIA NIM. Ask me about stock levels, purchase orders, or maintenance. I'm ready!"}
    ],
}


@app.get("/api/state")
async def get_state():
    return JSONResponse({
        "state": shared_state["state"],
        "last_query": shared_state["last_query"],
        "last_response": shared_state["last_response"],
        "last_metadata": shared_state["last_metadata"],
    })


@app.get("/api/conversation")
async def get_conversation():
    return JSONResponse(shared_state["conversation_log"])


@app.post("/api/query")
async def post_query(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return JSONResponse({"status": "error", "message": "Empty query"}, status_code=400)

    shared_state["state"] = "thinking"
    shared_state["last_query"] = text
    shared_state["conversation_log"].append({"role": "user", "content": text})

    response_text, metadata = brain.chat(text)

    shared_state["last_response"] = response_text
    shared_state["last_metadata"] = metadata
    shared_state["conversation_log"].append({"role": "assistant", "content": response_text})
    shared_state["state"] = "idle"

    return JSONResponse({"status": "ok", "response": response_text, "metadata": metadata})


@app.post("/api/reset")
async def reset():
    brain.reset_conversation()
    shared_state["conversation_log"] = []
    shared_state["last_query"] = ""
    shared_state["last_response"] = ""
    shared_state["last_metadata"] = {}
    shared_state["state"] = "idle"
    return JSONResponse({"status": "ok"})


# Serve static dashboard
static_dir = pathlib.Path(__file__).parent / "sap_warehouse_copilot" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
