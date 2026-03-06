"""
Robot Behavior Library — Expressive movements mapped to SAP data states.

Each behavior is a coroutine-style function that yields (head_pose, antennas, body_yaw)
frames for smooth animation. The main app loop consumes these frames via set_target().
"""

import math
import time
import numpy as np
from typing import Generator

try:
    from reachy_mini.utils import create_head_pose
except ImportError:
    # Fallback for dev without reachy_mini installed
    def create_head_pose(x=0, y=0, z=0, roll=0, pitch=0, yaw=0, degrees=True, mm=False):
        return np.eye(4)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FPS = 60
FRAME_DT = 1.0 / FPS


def _antenna_angles(left_deg: float, right_deg: float) -> np.ndarray:
    """Convert antenna angles in degrees to radians."""
    return np.deg2rad([left_deg, right_deg])


# ---------------------------------------------------------------------------
# Idle — Gentle breathing-like sway
# ---------------------------------------------------------------------------
def idle_behavior(duration: float = 5.0) -> Generator:
    """Calm, slow head sway. Used when waiting for input."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        yaw = 5 * math.sin(2 * math.pi * 0.15 * t)
        pitch = 3 * math.sin(2 * math.pi * 0.1 * t + 0.5)
        head = create_head_pose(yaw=yaw, pitch=pitch, degrees=True)
        antennas = _antenna_angles(10 + 5 * math.sin(2 * math.pi * 0.2 * t), 10 + 5 * math.sin(2 * math.pi * 0.2 * t + math.pi))
        yield head, antennas, np.deg2rad(0)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Listening — Tilt head, antennas perked up
# ---------------------------------------------------------------------------
def listening_behavior(duration: float = 3.0) -> Generator:
    """Head tilted slightly, antennas up — shows attentiveness."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        roll = 8 * math.sin(2 * math.pi * 0.3 * t)
        head = create_head_pose(yaw=0, pitch=-5, roll=roll, degrees=True)
        antennas = _antenna_angles(45, 45)  # perked up
        yield head, antennas, np.deg2rad(0)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Thinking — Antennas pulse, head looks up-left
# ---------------------------------------------------------------------------
def thinking_behavior(duration: float = 2.0) -> Generator:
    """Processing/querying SAP. Antennas wave, head tilts up-left."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        yaw = -15 + 5 * math.sin(2 * math.pi * 0.5 * t)
        pitch = -10
        head = create_head_pose(yaw=yaw, pitch=pitch, degrees=True)
        # Alternating antenna wave
        left = 30 + 30 * math.sin(2 * math.pi * 1.5 * t)
        right = 30 + 30 * math.sin(2 * math.pi * 1.5 * t + math.pi)
        antennas = _antenna_angles(left, right)
        yield head, antennas, np.deg2rad(-5)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Healthy / Good News — Happy nod + antenna celebration
# ---------------------------------------------------------------------------
def healthy_behavior(duration: float = 2.5) -> Generator:
    """Stock is healthy! Nodding + happy antennas."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        # Nodding motion
        pitch = 10 * math.sin(2 * math.pi * 1.5 * t)
        head = create_head_pose(yaw=0, pitch=pitch, degrees=True)
        # Happy antenna bounce
        bounce = 50 + 20 * abs(math.sin(2 * math.pi * 2.0 * t))
        antennas = _antenna_angles(bounce, bounce)
        yield head, antennas, np.deg2rad(0)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Reorder Warning — Side-to-side concern
# ---------------------------------------------------------------------------
def reorder_behavior(duration: float = 2.5) -> Generator:
    """Stock needs reorder. Concerned side-to-side movement."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        yaw = 20 * math.sin(2 * math.pi * 0.8 * t)
        head = create_head_pose(yaw=yaw, pitch=-5, degrees=True)
        # Antennas down and flickering
        flicker = 20 + 10 * math.sin(2 * math.pi * 3.0 * t)
        antennas = _antenna_angles(flicker, flicker)
        yield head, antennas, np.deg2rad(yaw * 0.3)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Critical Alert — Urgent shake + antennas flat
# ---------------------------------------------------------------------------
def critical_behavior(duration: float = 3.0) -> Generator:
    """CRITICAL stock or overdue PO! Fast head shake, antennas alarmed."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        # Fast shake
        yaw = 25 * math.sin(2 * math.pi * 3.0 * t) * max(0, 1 - t / duration)
        pitch = -8 + 5 * math.sin(2 * math.pi * 1.0 * t)
        head = create_head_pose(yaw=yaw, pitch=pitch, degrees=True)
        # Antennas alternating rapidly
        left = 60 * abs(math.sin(2 * math.pi * 4.0 * t))
        right = 60 * abs(math.sin(2 * math.pi * 4.0 * t + math.pi))
        antennas = _antenna_angles(left, right)
        yield head, antennas, np.deg2rad(yaw * 0.2)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Out of Stock — Dramatic head drop + sad antennas
# ---------------------------------------------------------------------------
def out_of_stock_behavior(duration: float = 3.0) -> Generator:
    """Zero stock! Head drops, antennas droop, then looks up urgently."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        progress = t / duration
        if progress < 0.4:
            # Head drops
            pitch = 15 * (progress / 0.4)
            antennas = _antenna_angles(5, 5)  # droopy
        else:
            # Snaps back up — urgent
            pitch = 15 - 25 * ((progress - 0.4) / 0.6)
            antennas = _antenna_angles(60, 60)  # alert
        head = create_head_pose(yaw=0, pitch=pitch, degrees=True)
        yield head, antennas, np.deg2rad(0)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Speaking — Subtle movements while delivering response
# ---------------------------------------------------------------------------
def speaking_behavior(duration: float = 4.0) -> Generator:
    """Natural micro-movements while robot 'speaks'."""
    t0 = time.time()
    while time.time() - t0 < duration:
        t = time.time() - t0
        yaw = 8 * math.sin(2 * math.pi * 0.4 * t)
        pitch = 3 * math.sin(2 * math.pi * 0.6 * t + 1.0)
        roll = 4 * math.sin(2 * math.pi * 0.25 * t)
        head = create_head_pose(yaw=yaw, pitch=pitch, roll=roll, degrees=True)
        antennas = _antenna_angles(
            25 + 10 * math.sin(2 * math.pi * 0.5 * t),
            25 + 10 * math.sin(2 * math.pi * 0.5 * t + 0.8),
        )
        yield head, antennas, np.deg2rad(yaw * 0.15)
        time.sleep(FRAME_DT)


# ---------------------------------------------------------------------------
# Behavior selector based on SAP metadata
# ---------------------------------------------------------------------------
def select_behavior(metadata: dict) -> Generator:
    """Pick the right robot behavior based on SAP query results."""
    health = metadata.get("stock_health")
    has_overdue = metadata.get("has_overdue", False)

    if health == "OUT_OF_STOCK":
        yield from out_of_stock_behavior()
    elif health == "CRITICAL" or health == "RED":
        yield from critical_behavior()
    elif has_overdue:
        yield from critical_behavior(duration=2.0)
    elif health == "REORDER" or health == "AMBER":
        yield from reorder_behavior()
    elif health == "HEALTHY" or health == "GREEN":
        yield from healthy_behavior()
    else:
        yield from speaking_behavior()
