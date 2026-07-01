#!/usr/bin/env python3
"""
test_audio_amp.py — Diagnose whether the MAX98357A amp SD pin needs to be driven HIGH.

This script performs an A/B test:
  A) Play a 440Hz tone WITHOUT driving the SD GPIO  → expect SILENCE  
  B) Drive GPIO4 HIGH, then play the tone           → expect SOUND

If you hear sound in test B but not test A, the SD pin hypothesis is confirmed.
"""

import subprocess
import time
import sys
import os

# --- Configuration ---
SD_GPIO = 4                 # GPIO pin for MAX98357A shutdown (BCM numbering)
TEST_WAV = os.path.join(os.path.dirname(__file__), "test_tone.wav")
APLAY_DEVICE = "hw:0,0"  # Direct hardware — bypasses dmix entirely

# --- Try importing GPIO ---
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("RPi.GPIO not available — cannot drive GPIO pins.")
    print("Try: pip install RPi.GPIO")
    GPIO_AVAILABLE = False

# --- Helpers ---
def play_tone(label: str):
    """Play the test WAV and report result."""
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  Playing: {TEST_WAV}")
    print(f"  Device:  {APLAY_DEVICE}")
    print(f"  Listen now...")

    result = subprocess.run(
        ["aplay", "-D", APLAY_DEVICE, TEST_WAV],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"  aplay exited OK (rc=0)")
    else:
        print(f"  aplay FAILED (rc={result.returncode})")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")

    return result.returncode


def main():
    print("=" * 50)
    print("  MAX98357A Amplifier SD Pin Test")
    print("=" * 50)
    print(f"  SD GPIO: BCM {SD_GPIO}")
    print(f"  WAV:     {TEST_WAV}")

    if not os.path.exists(TEST_WAV):
        print(f"\nERROR: Test WAV not found at {TEST_WAV}")
        print("Generate it with:")
        print('  ffmpeg -f lavfi -i "sine=frequency=440:duration=3" -ar 44100 -ac 2 -c:a pcm_s16le test_tone.wav -y')
        sys.exit(1)

    if not GPIO_AVAILABLE:
        print("\nCannot run GPIO test — RPi.GPIO not available.")
        print("Just playing the tone (amp may be in shutdown)...")
        play_tone("Playing WITHOUT GPIO control (whatever current state is)")
        sys.exit(1)

    # --- SETUP ---
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SD_GPIO, GPIO.OUT)

    try:
        # --- TEST A: GPIO LOW (shutdown / default float) ---
        print("\n--- TEST A: SD PIN LOW (amp in SHUTDOWN) ---")
        GPIO.output(SD_GPIO, GPIO.LOW)
        time.sleep(0.3)
        play_tone("TEST A: SD=LOW → Expect SILENCE")

        # --- Ask user ---
        print("\n⏸️  Did you hear the tone just now? (y/n): ", end="", flush=True)
        heard_a = sys.stdin.readline().strip().lower()

        # --- TEST B: GPIO HIGH (amp active) ---
        print("\n--- TEST B: SD PIN HIGH (amp ACTIVE) ---")
        GPIO.output(SD_GPIO, GPIO.HIGH)
        time.sleep(0.3)
        play_tone("TEST B: SD=HIGH → Expect SOUND")

        # --- Ask user ---
        print("\n⏸️  Did you hear the tone just now? (y/n): ", end="", flush=True)
        heard_b = sys.stdin.readline().strip().lower()

        # --- DIAGNOSIS ---
        print("\n" + "=" * 50)
        print("  RESULTS")
        print("=" * 50)
        print(f"  Test A (SD=LOW):  {'HEARD' if heard_a == 'y' else 'SILENT'}")
        print(f"  Test B (SD=HIGH): {'HEARD' if heard_b == 'y' else 'SILENT'}")

        if heard_a != 'y' and heard_b == 'y':
            print("\n✅ DIAGNOSIS CONFIRMED:")
            print("   The MAX98357A SD pin on GPIO{} must be driven HIGH".format(SD_GPIO))
            print("   for the amplifier to produce sound.")
            print("\n   RECOMMENDED FIX (choose one):")
            print("   A) Replace 'dtoverlay=hifiberry-dac' with 'dtoverlay=max98357a,sdmode={}' in /boot/firmware/config.txt".format(SD_GPIO))
            print("   B) Add GPIO initialization to listener_v2.py before audio playback")
        elif heard_a == 'y' and heard_b == 'y':
            print("\n⚠️  Heard sound in BOTH tests — SD pin may already be pulled high")
            print("   or the amp does not use GPIO{} for shutdown.".format(SD_GPIO))
        elif heard_a != 'y' and heard_b != 'y':
            print("\n❌ Heard NO sound in either test.")
            print("   Possible issues:")
            print("   - Wrong GPIO pin (try GPIO21 or GPIO18)")
            print("   - Speakers not connected to the bonnet")
            print("   - Volume knob on the bonnet turned down")
            print("   - Another hardware problem")
        else:
            print("\n🤔 Unexpected: heard sound when SD=LOW but not when SD=HIGH")
            print("   This suggests the SD pin logic is inverted or it's a different GPIO.")

    finally:
        # --- CLEANUP ---
        # Set SD back LOW to shut down the amp (save power)
        GPIO.output(SD_GPIO, GPIO.LOW)
        GPIO.cleanup([SD_GPIO])
        print("\nGPIO cleaned up. SD pin set LOW (amp shutdown).")


if __name__ == "__main__":
    main()
