# Huats Club 2026
#!/usr/bin/env python3
"""
uart.py  —  UART Reader + OSC Sender
=====================================
Runs on the "sensor" Pi that is physically connected to the UWB module.

Reads raw UART frames from the BU03-Kit, parses them into 8 distances (m),
applies per-anchor calibration offsets, then broadcasts each frame over OSC
to the "game" Pi running game.py.

OSC message sent:  /distances  <tag_id:int> <d0:float> ... <d7:float>

Run:
    python3 uart.py --tags 2 --host 192.168.1.XX --port 5005
"""

import argparse
import struct
import sys
import time

import serial
from pythonosc import udp_client

# ---------------------------------------------------------------------------
# Hardware / protocol constants  (must match game.py)
# ---------------------------------------------------------------------------
SERIAL_PORT  = "/dev/serial0"
BAUD_RATE    = 115200
FRAME_HEADER = b"\xaa\x25\x01"
FRAME_SIZE   = 37
TRAILER      = 0x55

# Per-anchor calibration offsets (metres).
ANCHOR_OFFSETS = {
    0: -0.162,
    1: -0.082,
    2: -0.060,
    3: -0.083,
    4: +0.158,
    5: +0.052,
}

MAX_BUF = 8192   # runaway guard: never let the buffer grow unbounded

# ---------------------------------------------------------------------------
# OSC defaults  (override with CLI flags)
# ---------------------------------------------------------------------------
DEFAULT_HOST = "192.168.254.189"   # <-- change to game Pi's IP
DEFAULT_PORT = 5005


# ---------------------------------------------------------------------------
# Frame parsing helpers
# ---------------------------------------------------------------------------
def parse_frame(frame: bytes):
    """Return list of 8 distances (m) or None if the frame is invalid."""
    if len(frame) != FRAME_SIZE:
        return None
    if frame[:3] != FRAME_HEADER or frame[-1] != TRAILER:
        return None
    distances = []
    for i in range(8):
        off = 3 + i * 4
        (mm,) = struct.unpack_from("<I", frame, off)
        distances.append(mm / 1000.0)
    return distances


def find_frames(buf: bytearray):
    """Extract all complete frames from the mutable byte buffer."""
    frames = []
    if len(buf) > MAX_BUF:
        del buf[:-2]
    while True:
        idx = buf.find(FRAME_HEADER)
        if idx < 0:
            if len(buf) > 2:
                del buf[:-2]
            break
        if idx > 0:
            del buf[:idx]
        if len(buf) < FRAME_SIZE:
            break
        candidate = bytes(buf[:FRAME_SIZE])
        if candidate[-1] == TRAILER:
            frames.append(candidate)
            del buf[:FRAME_SIZE]
        else:
            del buf[:1]
    return frames


# ---------------------------------------------------------------------------
# Main reader / sender loop
# ---------------------------------------------------------------------------
def run(n_tags: int, host: str, port: int):
    # Open OSC client (fire-and-forget UDP — no connection needed)
    osc = udp_client.SimpleUDPClient(host, port)
    print(f"[uart] OSC target → {host}:{port}")

    # Open serial port
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open {SERIAL_PORT}: {e}")
        sys.exit(1)
    ser.reset_input_buffer()
    print(f"[uart] Serial open on {SERIAL_PORT} @ {BAUD_RATE} baud")
    print(f"[uart] Tracking {n_tags} tag(s).  Press Ctrl-C to stop.\n")

    buf        = bytearray()
    frame_count = 0

    try:
        while True:
            try:
                data = ser.read(256)
            except Exception as e:
                print(f"[reader error] {e}")
                break

            if data:
                buf.extend(data)

            for raw in find_frames(buf):
                distances = parse_frame(raw)
                if distances is None:
                    continue

                # Apply calibration offsets
                for aid, off in ANCHOR_OFFSETS.items():
                    if aid < len(distances):
                        distances[aid] = max(0.0, distances[aid] + off)

                # Round-robin tag assignment (matches game.py logic)
                tag_id = frame_count % n_tags

                # Build OSC message:  /distances  tag_id  d0 d1 ... d7
                osc_args = [tag_id] + distances
                osc.send_message("/distances", osc_args)

                frame_count += 1
                if frame_count % 100 == 0:
                    print(f"[uart] {frame_count} frames sent  "
                          f"(last tag={tag_id}, "
                          f"d0={distances[0]:.3f}m)")

    except KeyboardInterrupt:
        print("\n[uart] Stopped by user.")
    finally:
        ser.close()
        print(f"[uart] Serial closed.  Total frames sent: {frame_count}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Read UWB UART frames and stream distances via OSC.")
    ap.add_argument("--tags", type=int, default=2,
                    help="Number of active tags (1..8). Default: 2.")
    ap.add_argument("--host", type=str, default=DEFAULT_HOST,
                    help=f"IP of the game Pi. Default: {DEFAULT_HOST}")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"UDP port to send OSC to. Default: {DEFAULT_PORT}")
    args = ap.parse_args()

    if not 1 <= args.tags <= 8:
        print("--tags must be between 1 and 8")
        sys.exit(1)

    run(args.tags, args.host, args.port)


if __name__ == "__main__":
    main()
