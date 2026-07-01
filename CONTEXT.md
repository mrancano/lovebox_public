# CONTEXT.md — Lovebox Project

> **Last Updated:** 2026-07-01 (post audio debugging session)
> **Purpose:** Give any AI agent working on this project a complete understanding of the system, what works, what doesn't, and how to debug iteratively with a human bridge.

---

## 1. Project Overview

The Lovebox is a DIY long-distance communication device. A sender transmits text, images, or audio via Telegram. The Raspberry Pi Zero 2W receives them, displays them on a TFT screen, optionally plays audio, and spins a physical heart (servo) to alert the recipient. A physical button lets the recipient acknowledge messages or send a heart reply.

---

## 2. Hardware Summary

| Component | Model | Interface | Notes |
|-----------|-------|-----------|-------|
| CPU | Raspberry Pi Zero 2 WH | — | ARM64, Wi-Fi, 40-pin GPIO |
| Display | Elegoo 3.5" TFT | SPI (SPI0, CE0) | 480×320, ILI9486 driver, DC=GPIO24, RST=GPIO25 |
| Audio Amp | Adafruit I2S 3W Class D Bonnet (PID 3346) | I2S (PCM5102A / MAX98357A) | Uses `hifiberry-dac` overlay; SD pin NOT needed |
| Speakers | 3W 4Ω stereo enclosed | Terminal block on bonnet | |
| Servo | TowerPro SG90 | PWM on GPIO12 | 0°–180°, pulse 0.5ms–2.4ms |
| Button | 16mm illuminated momentary | GPIO3 (pull-up) | Press = LOW; physical pull-up on pin 3 |

### GPIO Pin Map

| GPIO | Function | Notes |
|------|----------|-------|
| GPIO3 (BCM) | Push button | Physical pull-up; LOW when pressed |
| GPIO12 (BCM) | Servo PWM | 50 Hz software PWM (RPi.GPIO) |
| GPIO24 (BCM) | Display DC | Data/Command for ILI9486 |
| GPIO25 (BCM) | Display RST | Reset for ILI9486 |
| GPIO7-11 | SPI0 (display) | CE1, CE0, MISO, MOSI, SCLK |
| GPIO18-21 | I2S audio | BCLK, LRCLK, DOUT, DIN |

---

## 3. Software Architecture

```
lovebox/
├── listener_v2.py          # MAIN ENTRY POINT — Telegram bot + orchestration
├── controllers/
│   ├── __init__.py          # Re-exports all controllers
│   ├── display_controller.py # ILI9486 TFT via luma.lcd (SPI)
│   ├── servo_controller.py  # SG90 servo via RPi.GPIO PWM
│   ├── audio_controller.py  # FFmpeg-based WAV conversion
│   └── text_to_png.py       # Renders text → PNG for display
├── testing/                 # Hardware test scripts
│   ├── test_audio_amp.py    # SD pin A/B test
│   ├── test_integration_audio.py # Step-by-step HW init + audio test
│   ├── test_tone.wav        # 440Hz test tone for diagnostics
│   ├── button_toggle.py     # Tests button + servo interaction
│   ├── test_display_controller.py
│   ├── test_display_sweep.py
│   ├── test_dotenv.py
│   ├── test_LED.py
│   └── test_mechanical.py
├── requirements.txt
├── setup.sh                # One-time provisioning (has `mpv'` typo!)
├── run.sh                  # Starts listener_v2.py in venv
├── update.sh               # git pull
└── .env                    # Contains TELEGRAM_KEY and MY_CHAT_ID
```

### Data Flow

```
Telegram → listener_v2.py (python-telegram-bot polling)
  ├─ text  → text_to_png() → display_controller.display_image()
  ├─ photo → display_controller.display_image()
  ├─ audio/voice → audio_controller.convert_to_wav() → aplay -D hw:0,0
  └─ video → (not implemented, just sleeps)

Button → GPIO callback → handle_button_press()
  ├─ If playing: cancel current task
  └─ If idle: send ❤️ reply via Telegram
```

---

## 4. What Works ✅

| Feature | Status | Details |
|---------|--------|---------|
| Telegram bot polling | ✅ | Receives all message types |
| Text display | ✅ | Converts text → PNG → TFT screen |
| Image display | ✅ | Downloads and displays photos; handles color profiles |
| Servo movement | ✅ | Moves to 180° on message, back to 0° on finish |
| Button cancel | ✅ | Cancels active playback; sends ❤️ when idle |
| Audio download + conversion | ✅ | Downloads from Telegram, FFmpeg → WAV |
| Display controller | ✅ | ILI9486 with luma.lcd, correct orientation, color correction |
| Audio in isolation | ✅ | `aplay -D hw:0,0` works when I2S driver is healthy |
| RPi.GPIO + audio coexistence | ✅ | Servo PWM does NOT corrupt I2S |

---

## 5. The Audio Problem — Full Diagnostic History

### 5.1 Original Symptom
When a voice message arrives: file downloads, FFmpeg converts to WAV, aplay runs and returns rc=0 — but **no sound from speakers**.

### 5.2 Layer 1: Wrong ALSA Device
The original code used `plughw:0,0`. The Adafruit i2samp installer created `/etc/asound.conf` with a dmix (software mixing) layer that takes exclusive access to `hw:0,0`. Result: `plughw:0,0` → "Device or resource busy".

**Fix applied:** Changed to `hw:0,0` in `listener_v2.py`.

### 5.3 Layer 2: The aplay.service Zombie
The Adafruit installer also created `/etc/systemd/system/aplay.service` which runs:
```
/usr/bin/aplay -D default -t raw -r 44100 -c 2 -f S16_LE /dev/zero
```
This continuously plays silence through the `default` (dmix) device to prevent I2S clock popping. It acts as the dmix "server" process. If killed, dmix breaks silently — aplay reports rc=0 but nothing reaches the DAC.

**Fix applied:** `sudo systemctl disable aplay.service` (permanent).

### 5.4 Layer 3: I2S Hardware Lockup After SIGKILL
Force-killing aplay mid-DMA-transfer can leave the I2S peripheral in a bad state. After this, even `hw:0,0` produces no sound. Only a module reload or reboot fixes it.

**Fix:** Reload I2S modules (temporary) or reboot. Also avoid SIGKILL-ing audio processes.

### 5.5 Layer 4: SPI Display + I2S DMA Conflict (SOLVED)

The Pi Zero 2W has a limited number of DMA channels. When the SPI display initializes, it steals the DMA channel that the I2S driver (`snd_soc_bcm2835_i2s`) was using. Once stolen, the I2S driver never reclaims it — even after SPI is released via `spidev.close()`. The driver must be reloaded to force a fresh DMA allocation.

**Root cause:** `dtoverlay=i2s-mmap` (added by the Adafruit installer alongside `hifiberry-dac`) made the conflict worse, but removing it wasn't enough — the core DMA contention between SPI and I2S remains regardless.

**Solution — multi-layered fix:**

1. **ALSA device:** Use `hw:0,0` (direct hardware) instead of `plughw:0,0` or `default` to bypass the fragile dmix layer from `/etc/asound.conf`.

2. **Disable aplay.service:** `sudo systemctl disable aplay.service` — this Adafruit-installed service continuously plays `/dev/zero` through dmix to prevent I2S clock popping, but it locks the audio device and breaks silently if killed.

3. **Remove i2s-mmap overlay:** Removed `dtoverlay=i2s-mmap` from `/boot/firmware/config.txt` to reduce DMA contention.

4. **On-demand display with I2S reload:** The display is never held open between messages. It is created on-demand for text/photo messages, used, set to black, and then `DisplayController.close()` is called which:
   - Closes the SPI device (`spidev.close()`)
   - Reloads the I2S kernel modules (`modprobe -r` then `modprobe` for `snd_soc_bcm2835_i2s`, `snd_soc_pcm5102a`, `snd_soc_rpi_simple_soundcard`)
   - This forces the I2S driver to re-allocate its DMA channel fresh
   
   For audio messages, the display is never touched — I2S already has the DMA channel from the last reload.

**Verified working flow (2026-07-01):**
- Text → display created → shown for 5s → black → close (reloads I2S) → audio ready
- Photo → display created → shown for 5s → black → close (reloads I2S) → audio ready  
- Voice/Audio → I2S already loaded → plays correctly ✅
---

## 6. Known Issues & Technical Debt

### 6.1 setup.sh Typo
```bash
sudo apt-get install -y ... mpv'   # ← trailing single quote, mpv never installed
```
Should be `mpv` without the quote.

### 6.2 ALSA /etc/asound.conf is Fragile
The dmix + softvol chain from the Adafruit installer is unnecessary for a single-user device. Consider simplifying to just use `hw:0,0` directly.

### 6.3 No Cleanup of Servo on Shutdown
`listener_v2.py`'s `main()` does not call `state.servo.cleanup()` on exit. Add to the `finally` block.

### 6.4 SD Card I/O Errors
Kernel log shows `I/O error, dev mmcblk0` — possible SD card corruption. Monitor. Consider replacing the SD card if errors increase.

---

## 7. Current Boot Config (`/boot/firmware/config.txt`)

```
dtparam=spi=on
dtoverlay=vc4-kms-v3d
dtoverlay=dwc2,dr_mode=host
dtoverlay=hifiberry-dac
# dtoverlay=i2s-mmap  ← REMOVED 2026-07-01 (DMA conflict with SPI)
```

---

## 8. Remaining Tasks

### 8.1 High Priority
1. **Fix setup.sh typo:** Change `mpv'` to `mpv` in the apt-get install line
2. **Add servo cleanup on shutdown:** `listener_v2.py`'s `main()` does not call `state.servo.cleanup()` on exit — add to the `finally` block
3. **Simplify /etc/asound.conf:** The dmix + softvol chain is unnecessary — could be simplified to just use `hw:0,0`, though this is cosmetic since we bypass it anyway

### 8.2 Low Priority
4. **Monitor SD card:** Kernel log shows `I/O error, dev mmcblk0` — possible card corruption
5. **Consider `mpv` as aplay alternative:** More format-tolerant, but requires fixing the setup.sh typo first
6. **Reduce I2S reload latency:** The module reload takes ~1 second. Could potentially just reload `snd_soc_bcm2835_i2s` instead of all three modules to speed it up---

## 9. Environment Details

- **OS:** Raspberry Pi OS (Debian 13/Bookworm-based, ARM64)
- **Python:** 3.x (venv at `/home/mrancano/src/lovebox/.venv`)
- **Audio tools:** `aplay` (ALSA), `ffmpeg` (conversion), `amixer` (mixer control)
- **Not installed:** `mpv` (typo in setup.sh)
- **Telegram media:** Saved to `/home/mrancano/telegram_media/` (cleaned after each message)
- **ALSA card:** `snd_rpi_hifiberry_dac` on `hw:0,0`
- **Stderr capture:** Now enabled for both FFmpeg and aplay subprocesses

---

## 10. Iterative Debugging Protocol

Since I (the AI agent) cannot see the physical box, hear audio, or observe servo movement, **you (the human) are my bridge to reality.**

### The "Test → Report" Loop

1. I write a small, focused test script or command
2. You run it on the Pi
3. You report EXACTLY what you observe (screen, audio, servo, LED, terminal output)
4. I analyze and write the next step

### Reporting Template

```
TEST: [name of test]
SCREEN: [what appeared on display, if anything]
AUDIO: [what you heard — silence / static / actual audio / clicks]
SERVO: [did it move? to what angle?]
BUTTON LED: [on/off/blinking]
AMP LED: [if the bonnet has a power LED, is it on?]
TERMINAL: [paste any printed output]
```

### Debugging Rules

1. **I will never assume something works** unless you confirm it.
2. **One change at a time.**
3. **All test scripts go in `testing/`.** Production code is only modified when confident.
4. **Stderr is captured.**
5. **Test hardware in isolation first**, then integrated.

---

## 11. Key Files Reference

| File | Purpose |
|------|---------|
| `listener_v2.py` | Main bot: message handling, GPIO, orchestration |
| `controllers/audio_controller.py` | FFmpeg WAV conversion (now captures stderr) |
| `controllers/display_controller.py` | ILI9486 TFT via luma.lcd + color correction |
| `controllers/servo_controller.py` | SG90 PWM control via RPi.GPIO |
| `controllers/text_to_png.py` | Text rendering for display |
| `testing/test_audio_amp.py` | SD pin A/B diagnostic |
| `testing/test_integration_audio.py` | Step-by-step HW+audio isolation test |
| `testing/test_tone.wav` | 440Hz 3s stereo test tone |
| `setup.sh` | One-time provisioning (has mpv typo) |
| `/etc/asound.conf` | ALSA config (dmix+softvol, from Adafruit) |
| `/etc/systemd/system/aplay.service` | DISABLED — was playing /dev/zero through dmix |
| `/boot/firmware/config.txt` | Device tree overlays (i2s-mmap REMOVED) |

---

*This document should be updated as we discover new information about the hardware or fix issues.*
