"""
SAP Warehouse Copilot — Main Reachy Mini App.

Orchestrates:
  1. Reachy Mini robot behaviors (head, antennas, body)
  2. NVIDIA NIM LLM with SAP tool-calling
  3. NVIDIA Riva Speech AI (ASR/TTS) — optional
  4. Gradio web dashboard served via FastAPI

Architecture:
  ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
  │  Riva ASR    │────▶│  NIM LLM       │────▶│  Riva TTS    │
  │  (Speech→Txt)│     │  + SAP Tools   │     │  (Txt→Speech)│
  └──────────────┘     └────────────────┘     └──────────────┘
         │                     │                      │
         │              ┌──────▼──────┐               │
         │              │  SAP OData  │               │
         │              │  Mock Layer │               │
         │              └─────────────┘               │
         │                     │                      │
         └─────────┬───────────┼──────────────────────┘
                   ▼           ▼
            ┌─────────────────────────┐
            │    Reachy Mini Robot    │
            │  (behaviors + speech)   │
            └─────────────────────────┘
"""

import logging
import threading
import time
import json
from typing import Optional

import numpy as np

from reachy_mini import ReachyMini, ReachyMiniApp

from .nvidia_brain import NVIDIABrain
from .robot_behaviors import (
    idle_behavior,
    listening_behavior,
    thinking_behavior,
    speaking_behavior,
    select_behavior,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


class SAPWarehouseCopilot(ReachyMiniApp):
    """
    SAP Warehouse Copilot — Voice-driven inventory assistant for Reachy Mini.

    Powered by NVIDIA NIM (LLM), Riva Speech AI (ASR/TTS), and SAP OData.
    """

    # URL for the Gradio web dashboard (served from static/)
    custom_app_url: str | None = None

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):
        """Main app loop — runs in background thread."""

        logger.info("=== SAP Warehouse Copilot starting ===")
        logger.info("Initializing NVIDIA Brain (NIM + Riva)...")

        brain = NVIDIABrain()

        # ------------------------------------------------------------------
        # State machine
        # ------------------------------------------------------------------
        STATE_IDLE = "idle"
        STATE_LISTENING = "listening"
        STATE_THINKING = "thinking"
        STATE_SPEAKING = "speaking"

        state = STATE_IDLE
        pending_query: Optional[str] = None
        response_text: Optional[str] = None
        response_metadata: dict = {}
        audio_playing = False

        # Shared state for the web UI (thread-safe via simple flags)
        shared_state = {
            "state": STATE_IDLE,
            "last_query": "",
            "last_response": "",
            "last_metadata": {},
            "conversation_log": [],
            "pending_text_query": None,  # Set by web UI
        }

        # ------------------------------------------------------------------
        # Audio handling
        # ------------------------------------------------------------------
        has_media = False
        try:
            reachy_mini.media.start_recording()
            reachy_mini.media.start_playing()
            has_media = True
            logger.info("Audio I/O initialized.")
        except Exception as e:
            logger.warning(f"Audio init failed (ok for sim): {e}")

        # ------------------------------------------------------------------
        # Start web server for dashboard
        # ------------------------------------------------------------------
        web_thread = threading.Thread(
            target=self._start_web_server,
            args=(shared_state, brain),
            daemon=True,
        )
        web_thread.start()

        # ------------------------------------------------------------------
        # Welcome greeting
        # ------------------------------------------------------------------
        logger.info("Playing welcome greeting...")
        welcome = "Hello! I'm your SAP Warehouse Copilot, powered by NVIDIA. Ask me about stock levels, purchase orders, or maintenance. I'm ready!"

        shared_state["last_response"] = welcome
        shared_state["conversation_log"].append({"role": "assistant", "content": welcome})

        # Play welcome animation
        for frame in idle_behavior(duration=2.0):
            if stop_event.is_set():
                break
            head, antennas, body_yaw = frame
            reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

        # TTS for welcome
        if brain.riva_available and has_media:
            audio = brain.text_to_speech(welcome)
            if audio is not None:
                reachy_mini.media.push_audio_sample(audio.reshape(-1, 1))

        # ------------------------------------------------------------------
        # Main loop
        # ------------------------------------------------------------------
        logger.info("Entering main loop...")

        while not stop_event.is_set():
            # Check for text input from web UI
            if shared_state.get("pending_text_query"):
                pending_query = shared_state["pending_text_query"]
                shared_state["pending_text_query"] = None
                state = STATE_THINKING

            # Check for voice input (Direction of Arrival detection)
            if state == STATE_IDLE and has_media and brain.riva_available:
                try:
                    doa, is_speech = reachy_mini.media.get_DoA()
                    if is_speech:
                        state = STATE_LISTENING
                except Exception:
                    pass

            # ------- STATE MACHINE -------

            if state == STATE_IDLE:
                shared_state["state"] = STATE_IDLE
                for frame in idle_behavior(duration=1.0):
                    if stop_event.is_set() or shared_state.get("pending_text_query"):
                        break
                    head, antennas, body_yaw = frame
                    reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

            elif state == STATE_LISTENING:
                shared_state["state"] = STATE_LISTENING
                logger.info("Listening for speech...")

                # Animate listening pose
                listen_gen = listening_behavior(duration=4.0)
                audio_chunks = []

                for frame in listen_gen:
                    if stop_event.is_set():
                        break
                    head, antennas, body_yaw = frame
                    reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

                    # Capture audio
                    if has_media:
                        try:
                            samples = reachy_mini.media.get_audio_sample()
                            if samples is not None:
                                audio_chunks.append(samples)
                        except Exception:
                            pass

                # Process captured audio through Riva ASR
                if audio_chunks:
                    full_audio = np.concatenate(audio_chunks, axis=0)
                    # Use first channel if stereo
                    if full_audio.ndim > 1:
                        full_audio = full_audio[:, 0]
                    transcript = brain.speech_to_text(full_audio)
                    if transcript.strip():
                        pending_query = transcript
                        state = STATE_THINKING
                        logger.info(f"ASR transcript: {transcript}")
                    else:
                        state = STATE_IDLE
                else:
                    state = STATE_IDLE

            elif state == STATE_THINKING:
                shared_state["state"] = STATE_THINKING
                shared_state["last_query"] = pending_query or ""
                shared_state["conversation_log"].append({"role": "user", "content": pending_query or ""})

                logger.info(f"Querying NIM: {pending_query}")

                # Animate thinking
                think_gen = thinking_behavior(duration=1.5)
                think_thread_done = threading.Event()
                nim_result = [None, None]

                def _call_nim():
                    text, meta = brain.chat(pending_query or "")
                    nim_result[0] = text
                    nim_result[1] = meta
                    think_thread_done.set()

                nim_thread = threading.Thread(target=_call_nim, daemon=True)
                nim_thread.start()

                # Play thinking animation while NIM processes
                for frame in think_gen:
                    if stop_event.is_set():
                        break
                    head, antennas, body_yaw = frame
                    reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

                # Wait for NIM if still processing
                think_thread_done.wait(timeout=15.0)
                response_text = nim_result[0] or "Sorry, I couldn't process that."
                response_metadata = nim_result[1] or {}

                shared_state["last_response"] = response_text
                shared_state["last_metadata"] = response_metadata
                shared_state["conversation_log"].append({"role": "assistant", "content": response_text})

                logger.info(f"NIM response: {response_text[:100]}...")

                state = STATE_SPEAKING
                pending_query = None

            elif state == STATE_SPEAKING:
                shared_state["state"] = STATE_SPEAKING

                # Play behavior based on SAP data health
                for frame in select_behavior(response_metadata):
                    if stop_event.is_set():
                        break
                    head, antennas, body_yaw = frame
                    reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

                # TTS output
                if brain.riva_available and has_media and response_text:
                    audio = brain.text_to_speech(response_text)
                    if audio is not None:
                        reachy_mini.media.push_audio_sample(audio.reshape(-1, 1))
                        # Animate while speaking
                        speak_duration = len(audio) / 16000.0
                        for frame in speaking_behavior(duration=speak_duration):
                            if stop_event.is_set():
                                break
                            head, antennas, body_yaw = frame
                            reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)
                else:
                    # No TTS — just animate speaking
                    for frame in speaking_behavior(duration=2.0):
                        if stop_event.is_set():
                            break
                        head, antennas, body_yaw = frame
                        reachy_mini.set_target(head=head, antennas=antennas, body_yaw=body_yaw)

                state = STATE_IDLE

            time.sleep(0.01)

        # ------------------------------------------------------------------
        # Cleanup
        # ------------------------------------------------------------------
        if has_media:
            try:
                reachy_mini.media.stop_recording()
                reachy_mini.media.stop_playing()
            except Exception:
                pass

        logger.info("=== SAP Warehouse Copilot stopped ===")

    def _start_web_server(self, shared_state: dict, brain: NVIDIABrain):
        """Start a FastAPI + static file server for the dashboard UI."""
        try:
            from fastapi import FastAPI, Request
            from fastapi.staticfiles import StaticFiles
            from fastapi.responses import JSONResponse
            import uvicorn
            import pathlib

            app = FastAPI(title="SAP Warehouse Copilot")

            # API endpoints for the web dashboard
            @app.get("/api/state")
            async def get_state():
                return JSONResponse({
                    "state": shared_state.get("state", "idle"),
                    "last_query": shared_state.get("last_query", ""),
                    "last_response": shared_state.get("last_response", ""),
                    "last_metadata": shared_state.get("last_metadata", {}),
                })

            @app.get("/api/conversation")
            async def get_conversation():
                return JSONResponse(shared_state.get("conversation_log", []))

            @app.post("/api/query")
            async def post_query(request: Request):
                body = await request.json()
                text = body.get("text", "").strip()
                if text:
                    shared_state["pending_text_query"] = text
                    return JSONResponse({"status": "queued", "text": text})
                return JSONResponse({"status": "error", "message": "Empty query"}, status_code=400)

            @app.post("/api/reset")
            async def reset():
                brain.reset_conversation()
                shared_state["conversation_log"] = []
                shared_state["last_query"] = ""
                shared_state["last_response"] = ""
                shared_state["last_metadata"] = {}
                return JSONResponse({"status": "ok"})

            # Serve static files
            static_dir = pathlib.Path(__file__).parent / "static"
            if static_dir.exists():
                app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

            uvicorn.run(app, host="0.0.0.0", port=7860, log_level="warning")

        except Exception as e:
            logger.error(f"Web server failed: {e}")
