"""
NVIDIA Brain — NIM LLM (function-calling) + Riva Speech AI (ASR/TTS).

Uses NVIDIA's cloud APIs via build.nvidia.com:
  - NIM: OpenAI-compatible chat completions with tool/function calling
  - Riva: gRPC-based ASR (speech→text) and TTS (text→speech)

Fallback: If Riva is unavailable, falls back to NIM-only mode with
text input/output (the Gradio UI handles mic recording separately).
"""

import json
import logging
import os
import io
import wave
import struct
from typing import Optional

import numpy as np
from openai import OpenAI

from .sap_mock import SAP_TOOLS, SAP_FUNCTION_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (set via env vars or .env)
# ---------------------------------------------------------------------------
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NIM_BASE_URL = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_MODEL = os.environ.get("NIM_MODEL", "meta/llama-3.1-70b-instruct")

# Groq fallback
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

# Riva cloud endpoint (gRPC)
RIVA_ASR_URI = os.environ.get("RIVA_ASR_URI", "grpc.nvcf.nvidia.com:443")
RIVA_TTS_URI = os.environ.get("RIVA_TTS_URI", "grpc.nvcf.nvidia.com:443")
RIVA_ASR_FUNCTION_ID = os.environ.get("RIVA_ASR_FUNCTION_ID", "")
RIVA_TTS_FUNCTION_ID = os.environ.get("RIVA_TTS_FUNCTION_ID", "")

# System prompt for the warehouse copilot persona
SYSTEM_PROMPT = """You are **SAP Warehouse Copilot**, an AI assistant embodied in a Reachy Mini robot.
You help warehouse managers and operators query SAP data using natural language.

Your capabilities (via SAP OData tools):
- Check stock levels for any material
- Look up material master data
- List purchase orders (filter by material or status)
- View plant maintenance work orders
- Provide overall warehouse KPI summaries

Behavior rules:
1. ALWAYS use the provided tools to answer SAP-related questions. Never fabricate data.
2. After calling a tool, summarize the result conversationally in 1-3 sentences.
3. If stock health is CRITICAL or OUT_OF_STOCK, flag it urgently.
4. If a purchase order is Overdue, highlight it and suggest follow-up.
5. Keep responses concise — you're speaking through a robot, not writing an essay.
6. When unsure which material the user means, ask for clarification.
7. For greetings or non-SAP questions, be friendly but steer back to warehouse topics.
8. End critical alerts with "I recommend immediate action."
9. Include the material number and description in your responses for clarity.

You are powered by NVIDIA NIM and run on Reachy Mini hardware.
"""


class NVIDIABrain:
    """Orchestrates NIM LLM inference with SAP tool-calling."""

    def __init__(self):
        if NVIDIA_API_KEY:
            self.client = OpenAI(base_url=NIM_BASE_URL, api_key=NVIDIA_API_KEY)
            self.model = NIM_MODEL
            self.provider = "NVIDIA NIM"
            logger.info(f"Using NVIDIA NIM: {NIM_MODEL}")
        elif GROQ_API_KEY:
            self.client = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
            self.model = GROQ_MODEL
            self.provider = "Groq"
            logger.info(f"NVIDIA_API_KEY not set — falling back to Groq: {GROQ_MODEL}")
        else:
            self.client = OpenAI(base_url=NIM_BASE_URL, api_key="demo-key")
            self.model = NIM_MODEL
            self.provider = "demo"
            logger.warning("No API keys set — using demo mode with limited responses.")
        self.conversation_history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.riva_available = self._check_riva()

    def _check_riva(self) -> bool:
        """Check if Riva gRPC client is importable and configured."""
        try:
            import riva.client
            if RIVA_ASR_FUNCTION_ID and RIVA_TTS_FUNCTION_ID:
                logger.info("Riva Speech AI available.")
                return True
        except ImportError:
            pass
        logger.info("Riva not available — text-only mode.")
        return False

    # ------------------------------------------------------------------
    # Speech → Text (Riva ASR)
    # ------------------------------------------------------------------
    def speech_to_text(self, audio_samples: np.ndarray, sample_rate: int = 16000) -> str:
        """Convert audio numpy array to text using Riva ASR cloud API."""
        if not self.riva_available:
            return ""

        try:
            import riva.client
            import grpc

            metadata = [
                ("function-id", RIVA_ASR_FUNCTION_ID),
                ("authorization", f"Bearer {NVIDIA_API_KEY}"),
            ]
            auth = riva.client.Auth(
                ssl_cert=None,
                use_ssl=True,
                uri=RIVA_ASR_URI,
                metadata_args=metadata,
            )
            asr_service = riva.client.ASRService(auth)

            # Convert float32 → int16 PCM
            audio_int16 = (audio_samples * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            config = riva.client.RecognitionConfig(
                language_code="en-US",
                max_alternatives=1,
                enable_automatic_punctuation=True,
                audio_channel_count=1,
                sample_rate_hertz=sample_rate,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
            )

            response = asr_service.offline_recognize(audio_bytes, config)
            if response.results:
                return response.results[0].alternatives[0].transcript
            return ""

        except Exception as e:
            logger.error(f"Riva ASR error: {e}")
            return ""

    # ------------------------------------------------------------------
    # Text → Speech (Riva TTS)
    # ------------------------------------------------------------------
    def text_to_speech(self, text: str, sample_rate: int = 16000) -> Optional[np.ndarray]:
        """Convert text to audio using Riva TTS cloud API. Returns float32 numpy array."""
        if not self.riva_available:
            return None

        try:
            import riva.client
            import grpc

            metadata = [
                ("function-id", RIVA_TTS_FUNCTION_ID),
                ("authorization", f"Bearer {NVIDIA_API_KEY}"),
            ]
            auth = riva.client.Auth(
                ssl_cert=None,
                use_ssl=True,
                uri=RIVA_TTS_URI,
                metadata_args=metadata,
            )
            tts_service = riva.client.SpeechSynthesisService(auth)

            response = tts_service.synthesize(
                text,
                voice_name="English-US.Female-1",
                language_code="en-US",
                sample_rate_hz=sample_rate,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
            )

            # Convert bytes → float32 numpy
            audio_int16 = np.frombuffer(response.audio, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32767.0
            return audio_float

        except Exception as e:
            logger.error(f"Riva TTS error: {e}")
            return None

    # ------------------------------------------------------------------
    # LLM Chat with SAP Tool Calling (NIM)
    # ------------------------------------------------------------------
    def chat(self, user_message: str) -> tuple[str, dict]:
        """
        Send user message to NIM, handle tool calls, return (response_text, metadata).

        metadata includes:
          - tool_calls: list of {name, args, result}
          - stock_health: str or None (HEALTHY/REORDER/CRITICAL/OUT_OF_STOCK)
          - has_overdue: bool
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        metadata = {"tool_calls": [], "stock_health": None, "has_overdue": False}

        try:
            # First call — may include tool_calls
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=SAP_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )

            assistant_msg = response.choices[0].message

            # Handle tool calls if present
            if assistant_msg.tool_calls:
                # Add assistant message with tool calls
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in assistant_msg.tool_calls
                    ]
                })

                # Execute each tool call
                for tc in assistant_msg.tool_calls:
                    func_name = tc.function.name
                    func_args = json.loads(tc.function.arguments) if tc.function.arguments else {}

                    logger.info(f"Tool call: {func_name}({func_args})")

                    if func_name in SAP_FUNCTION_MAP:
                        result = SAP_FUNCTION_MAP[func_name](func_args)
                    else:
                        result = {"error": f"Unknown function: {func_name}"}

                    result_str = json.dumps(result, indent=2, default=str)

                    metadata["tool_calls"].append({
                        "name": func_name,
                        "args": func_args,
                        "result": result,
                    })

                    # Extract health signals for robot behavior
                    if isinstance(result, dict):
                        if "health" in result:
                            metadata["stock_health"] = result["health"]
                        if "overall_health" in result:
                            metadata["stock_health"] = result["overall_health"]
                        if result.get("overdue_purchase_orders", 0) > 0:
                            metadata["has_overdue"] = True

                    if isinstance(result, list):
                        for item in result:
                            if isinstance(item, dict) and item.get("status") == "Overdue":
                                metadata["has_overdue"] = True

                    # Add tool result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                # Second call — generate natural language summary
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                    temperature=0.3,
                    max_tokens=512,
                )
                final_text = response.choices[0].message.content or "I processed the data but couldn't generate a summary."
            else:
                final_text = assistant_msg.content or "I'm not sure how to help with that. Try asking about stock levels, purchase orders, or maintenance."

            self.conversation_history.append({"role": "assistant", "content": final_text})

            # Keep conversation manageable (last 20 messages + system)
            if len(self.conversation_history) > 22:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-20:]

            return final_text, metadata

        except Exception as e:
            logger.error(f"NIM chat error: {e}")
            error_msg = f"I encountered an issue connecting to NVIDIA NIM: {str(e)[:100]}. Please check the API key configuration."
            return error_msg, metadata

    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
