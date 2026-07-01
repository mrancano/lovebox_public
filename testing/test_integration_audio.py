#!/usr/bin/env python3
"""
test_integration_audio.py — Mimics listener_v2.py's hardware initialization,
then attempts to play audio. This isolates whether servo/display init
breaks I2S audio output.
"""

import subprocess
import time
import sys
import os

# Allow importing from parent project directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_WAV = os.path.join(os.path.dirname(__file__), "test_tone.wav")
APLAY_DEVICE = "hw:0,0"  # Direct hardware — bypasses dmix entirely

print("=" * 50)
print("  INTEGRATION AUDIO TEST")
print("=" * 50)

# --- STEP 1: Play audio BEFORE any GPIO init (baseline) ---
print("\n--- STEP 1: Play BEFORE hardware init (baseline) ---")
result = subprocess.run(
    ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
    capture_output=True, text=True
)
print(f"  aplay rc={result.returncode}")
if result.stderr:
    print(f"  stderr: {result.stderr.strip()}")
print("  ⏸️  Did you hear the tone? (y/n): ", end="", flush=True)
heard_before = sys.stdin.readline().strip().lower()

# --- STEP 2: Init Servo (same as listener_v2.py) ---
print("\n--- STEP 2: Init ServoController (GPIO12, 50Hz PWM) ---")
try:
    from controllers.servo_controller import ServoController
    servo = ServoController()
    servo.go_to_degrees(0)
    print("  Servo initialized. Keeping PWM alive on GPIO12...")
except Exception as e:
    print(f"  Servo init FAILED: {e}")
    servo = None

# --- STEP 3: Play audio with servo active ---
print("\n--- STEP 3: Play WITH servo active ---")
result = subprocess.run(
    ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
    capture_output=True, text=True
)
print(f"  aplay rc={result.returncode}")
if result.stderr:
    print(f"  stderr: {result.stderr.strip()}")
print("  ⏸️  Did you hear the tone? (y/n): ", end="", flush=True)
heard_servo = sys.stdin.readline().strip().lower()

# --- STEP 4: Init Display (same as listener_v2.py) ---
print("\n--- STEP 4: Init DisplayController (SPI, ILI9486) ---")
try:
    from controllers.display_controller import DisplayController
    display = DisplayController()
    display.set_black()
    print("  Display initialized and set to black.")
except Exception as e:
    print(f"  Display init FAILED: {e}")
    display = None

# --- STEP 5: Play audio with both servo AND display active ---
print("\n--- STEP 5: Play WITH servo + display active ---")
result = subprocess.run(
    ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
    capture_output=True, text=True
)
print(f"  aplay rc={result.returncode}")
if result.stderr:
    print(f"  stderr: {result.stderr.strip()}")
print("  ⏸️  Did you hear the tone? (y/n): ", end="", flush=True)
heard_both = sys.stdin.readline().strip().lower()

# --- STEP 6: Move servo to 180° (simulating message alert) ---
if servo:
    print("\n--- STEP 6: Move servo to 180° + play ---")
    servo.go_to_degrees(180)
    result = subprocess.run(
        ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
        capture_output=True, text=True
    )
    print(f"  aplay rc={result.returncode}")
    if result.stderr:
        print(f"  stderr: {result.stderr.strip()}")
    print("  ⏸️  Did you hear the tone? (y/n): ", end="", flush=True)
    heard_180 = sys.stdin.readline().strip().lower()
    servo.go_to_degrees(0)
else:
    heard_180 = "n/a"

# --- STEP 7: Cleanup and test after cleanup ---
print("\n--- STEP 7: Cleanup servo, play again ---")
if servo:
    servo.cleanup()
    print("  Servo cleaned up.")
if display:
    display.set_black()
    print("  Display set black.")

time.sleep(0.5)

result = subprocess.run(
    ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
    capture_output=True, text=True
)
print(f"  aplay rc={result.returncode}")
if result.stderr:
    print(f"  stderr: {result.stderr.strip()}")
print("  ⏸️  Did you hear the tone? (y/n): ", end="", flush=True)
heard_after = sys.stdin.readline().strip().lower()

# --- RESULTS ---
print("\n" + "=" * 50)
print("  RESULTS")
print("=" * 50)
print(f"  STEP 1 (no HW):      {'HEARD ✅' if heard_before == 'y' else 'SILENT ❌'}")
print(f"  STEP 3 (servo):      {'HEARD ✅' if heard_servo == 'y' else 'SILENT ❌'}")
print(f"  STEP 5 (servo+disp): {'HEARD ✅' if heard_both == 'y' else 'SILENT ❌'}")
print(f"  STEP 6 (servo@180):  {'HEARD ✅' if heard_180 == 'y' else 'SILENT ❌'}")
print(f"  STEP 7 (cleaned up): {'HEARD ✅' if heard_after == 'y' else 'SILENT ❌'}")

# Diagnose
silent_steps = []
if heard_before != 'y': silent_steps.append("STEP 1 (no HW)")
if heard_servo != 'y': silent_steps.append("STEP 3 (servo)")
if heard_both != 'y': silent_steps.append("STEP 5 (servo+disp)")
if heard_180 != 'y': silent_steps.append("STEP 6 (servo@180)")
if heard_after != 'y': silent_steps.append("STEP 7 (cleaned up)")

if silent_steps:
    print(f"\n  Audio failed at: {', '.join(silent_steps)}")
else:
    print("\n  ✅ Audio worked at every step — issue may be with async subprocess or timing.")
