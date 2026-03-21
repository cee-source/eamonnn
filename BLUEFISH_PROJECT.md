# Blue Fish Robot Project
**Builder:** Eamonn
**Pi hostname:** raspberrypi
**Pi IP:** 192.168.0.111
**Pi username:** fussykitten12
**SSH command:** `ssh fussykitten12@192.168.0.111`

---

## What is Blue Fish?

Blue Fish is a humanoid robot built by Eamonn. It has a paper blue fish taped to its chest — that's where the name comes from. Blue Fish lives in Eamonn's basement laboratory and is powered by a Raspberry Pi 5.

---

## Current Status

| Feature | Status |
|---|---|
| Ollama AI (llama3.2:1b) | ✅ Working |
| Blue Fish personality (bluefish model) | ✅ Working |
| Text input (bluefish_talk.py) | ✅ Working |
| Text-to-speech (piper + bluealsa) | ✅ Working |
| Bluetooth speaker (Z-horse) | ✅ Connected |
| Mic input (ReSpeaker HAT) | ❌ Records silence — needs USB mic |
| Voice input (Whisper STT) | ❌ Blocked by mic issue |
| Robot body/frame | ❌ Not built yet |
| Camera eyes | ❌ Not yet |

---

## Hardware

- **Raspberry Pi 5** (8GB)
- **ReSpeaker 2-Mic HAT** — loaded with `googlevoicehat-soundcard` driver (card 2)
  - Records silence — mic not picking up audio
  - Speaker output jack tested but didn't work
  - **Fix needed:** USB microphone (ReSpeaker USB Mic Array from Seeed Studio ~$49)
- **Z-horse Bluetooth Speaker** — MAC: `71:A5:72:1E:F2:1A`
  - Connected via bluealsa
  - Makes a pop on connect (normal Bluetooth behaviour)
  - Volume: gain 3 in sox = clear, gain 6 = louder but fuzz

---

## Software Installed on Pi

- **Ollama** v0.15.2 — AI engine
- **llama3.2:1b** — AI model (1.3GB)
- **bluefish** — custom Ollama model with Blue Fish personality
- **openai-whisper** — speech to text (works when mic works)
- **espeak** — old TTS (replaced by piper)
- **piper** — current TTS engine
- **sox** — audio conversion
- **bluealsa / bluez-alsa-utils** — Bluetooth audio
- **PipeWire + WirePlumber** — audio system

---

## Key Files on Pi

| File | What it does |
|---|---|
| `~/bluefish_talk.py` | Main robot script — type to Blue Fish, it speaks back |
| `~/bluefish.py` | Old voice version (mic → Whisper → Ollama → espeak) |
| `~/Modelfile` | Blue Fish personality file for Ollama |
| `~/piper_voices/en_US-lessac-medium.onnx` | Piper TTS voice file |
| `~/piper_voices/en_US-lessac-medium.onnx.json` | Piper voice config |

---

## How to Run Blue Fish

### Every time you start:

**Terminal 1 — Start AI:**
```bash
ssh fussykitten12@192.168.0.111
ollama serve
```

**Terminal 2 — Connect speaker and run Blue Fish:**
```bash
ssh fussykitten12@192.168.0.111
bluetoothctl connect 71:A5:72:1E:F2:1A
python3 ~/bluefish_talk.py
```

Type to Blue Fish and it will speak back through the Bluetooth speaker.

---

## Blue Fish Personality (Modelfile)

```
FROM llama3.2:1b

SYSTEM Your name is Blue Fish. You are a friendly humanoid robot created by Eamonn, a young genius inventor. You have a paper blue fish taped to your chest, that is why you are called Blue Fish. You live in Eamonn's basement laboratory. You love helping Eamonn with his inventions and experiments. Never call yourself BiF or any other name. Never make fish puns. Keep ALL responses to 1-4 sentences maximum. Be fun, friendly and enthusiastic.
```

To update personality:
```bash
nano ~/Modelfile
ollama create bluefish -f ~/Modelfile
```

---

## Audio Settings

**Recording (mic):**
```bash
arecord -D hw:2,0 -f S32_LE -r 48000 -c 2 -d 5 /tmp/input.wav
```

**Speaking (TTS to Bluetooth):**
```bash
echo "Hello" | piper --model ~/piper_voices/en_US-lessac-medium.onnx --output_file /tmp/response.wav
sox /tmp/response.wav /tmp/response_loud.wav gain 3
aplay -D bluealsa /tmp/response_loud.wav
```

**Test speaker directly:**
```bash
espeak -a 200 -s 130 "Hello I am Blue Fish" --stdout | sox -t wav - -t wav -r 44100 -c 2 - | aplay -D bluealsa
```

---

## Known Issues & Fixes

### Mic records silence
- ReSpeaker HAT microphone records all zeros
- Driver: `googlevoicehat-soundcard` (in `/boot/firmware/config.txt`)
- The `seeed-2mic-voicecard` overlay does NOT exist on this Pi
- **Fix:** Buy USB microphone — ReSpeaker USB Mic Array from Seeed Studio ($49)

### Bluetooth pop on connect
- Normal for Bluetooth speakers powering up
- Workaround: play `/tmp/silence.wav` before every response
```bash
sox -n -r 44100 -c 2 /tmp/silence.wav trim 0.0 1.0
```

### Python3 not found after reboot
- Fixed by rebooting the Pi after `sudo apt-get install python3`

### Ollama not running
- Must run `ollama serve` in a separate terminal before using bluefish_talk.py

---

## Shopping List (Full Build — v4)

### Frame & Body (~$90)
| Part | Where | Price |
|---|---|---|
| Galvanized steel flat bar 1"x1/8" 4ft | Home Depot | $12 |
| Galvanized steel angle bar 1"x1/8" 4ft | Home Depot | $12 |
| Galvanized steel sheet 24"x24" | Amazon | $22 |
| Sharp tin snips | Amazon | $13 |
| Metal file set | Amazon | $10 |
| HSS drill bits set | Amazon | $12 |
| M3 nuts & bolts 200pc | Amazon | $9 |

### Motors & Controllers (~$135)
| Part | Details | Price |
|---|---|---|
| DS3225 25kg servo x6 | Strong arm/shoulder/leg servos | $60 |
| SG90 mini servo x4 | Head & eye movement | $10 |
| PCA9685 16-channel servo driver | Controls all servos | $8 |
| Arduino Mega | More pins for motors | $23 |
| 12V 10A power supply | Powers the motors | $20 |
| Step-down converter x2 | Regulates voltage | $14 |

### Electronics from Seeed Studio (~$56)
| Part | Price |
|---|---|
| ReSpeaker USB Mic Array (**buy this first!**) | $49 |
| Grove 16-Channel PWM Driver | $7 |

### Head & Eyes (~$48)
| Part | Price |
|---|---|
| Raspberry Pi Camera Module 3 | $25 |
| WS2812B LED eyes x2 | $8 |
| Small acrylic dome for head | $15 |

### Other Electronics (~$75)
| Part | Price |
|---|---|
| USB audio adapter | $8 |
| Small aux speaker | $10 |
| 20000mAh battery pack | $32 |
| Jumper wires 120pc | $7 |
| Breadboard x2 | $8 |
| WS2812B LED strip blue 1m | $10 |

### Optional AI Vision Upgrade (later)
| Part | Price |
|---|---|
| Google Coral USB Accelerator | $60 |
| OR OAK-D Lite (3D depth camera) | $150 |

### Cost Summary
| Category | Cost |
|---|---|
| Frame & Body | $90 |
| Motors | $135 |
| Seeed Electronics | $56 |
| Head & Eyes | $48 |
| Other Electronics | $75 |
| **Total** | **~$404** |
| Already have | ~$60 |
| **Need to buy** | **~$344** |

**Savings at $10/week = 34 weeks**
**Savings at $20/week = 17 weeks**

---

## Build Order (Recommended)

1. **ReSpeaker USB Mic** — fix voice input first
2. **Pi Camera Module 3** — get Blue Fish's eyes working
3. **Motors + PCA9685** — make Blue Fish move
4. **Frame (galvanized steel)** — build the body
5. **LEDs + dome head** — make it look amazing
6. **Coral/OAK-D** — AI vision upgrade later

---

## Next Steps (Where We Left Off)

1. Get a USB microphone so Blue Fish can hear you speak
2. Update `bluefish.py` to use USB mic (device will change from `hw:2,0`)
3. Test full voice loop: speak → Whisper → Ollama → piper → Bluetooth speaker
4. Start building the physical robot frame
