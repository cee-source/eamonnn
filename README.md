# Soccer 8-Ball

A Magic 8-Ball for soccer fans, built on a Raspberry Pi Zero. Ask it a
question out loud; it "thinks" by cross-checking a draft answer from an LLM
(Ollama) against several independent Google search results, then reveals its
verdict on a small screen: a soccer ball flies at the camera, one white
hexagon panel keeps zooming in until it fills the whole screen, and the
answer types itself on over the white.

If the search results don't clearly agree with each other, it says **"I
don't know"** instead of guessing.

## How the "is this actually true" check works

1. Ollama turns your question into a short factual claim + search query (or
   flags it as unanswerable opinion/luck, e.g. "will I win the lottery").
2. `soccerball8/search.py` fetches several independent results from Google
   Custom Search for that query.
3. `soccerball8/fact_check.py` asks Ollama to classify each result snippet as
   `SUPPORTS`, `CONTRADICTS`, or `UNRELATED` to the claim, then:
   - takes the fraction of relevant results that agree (the "stance
     probability"),
   - separately measures how much the supporting/contradicting snippets
     textually corroborate **each other** (independent of the claim), so one
     confident-sounding page can't dominate the vote,
   - blends both into one confidence score.
4. If there isn't enough relevant evidence, or confidence falls below
   `CONFIDENCE_THRESHOLD` (default 0.7), the answer is **"I don't know"**.
   Otherwise Ollama phrases the verdict as a short Magic-8-Ball-style line.

## Hardware

- Raspberry Pi Zero W or Zero 2 W (needs Wi-Fi to reach Ollama + Google)
- USB mini microphone (USB-A -> a micro-USB-OTG adapter for the Pi Zero's
  port, or use a Zero 2 W's USB port directly)
- A 2.4"-2.5" SPI TFT display, e.g. an ST7789V or ILI9341 panel (this
  project defaults to 240x320)
- A push button wired to a GPIO pin (default: GPIO17) + ground, to trigger
  listening (tilt/shake sensors work too if you'd rather wire one of those in
  place of the button)
- microSD card, power supply, case

### Wiring the screen (SPI)

| Display pin | Pi Zero pin        |
|-------------|--------------------|
| VCC         | 3V3                |
| GND         | GND                |
| SCL/SCK     | GPIO11 (SPI0 SCLK) |
| SDA/MOSI    | GPIO10 (SPI0 MOSI) |
| CS          | GPIO8 (SPI0 CE0)   |
| DC          | GPIO24 (configurable, `DISPLAY_GPIO_DC`) |
| RST         | GPIO25 (configurable, `DISPLAY_GPIO_RST`) |
| BL/LED      | 3V3 (or a GPIO + resistor if you want brightness control) |

Enable SPI first: `sudo raspi-config` -> Interface Options -> SPI -> Enable.

### Wiring the button

Button between `BUTTON_GPIO_PIN` (default GPIO17) and GND. `gpiozero`'s
`Button` uses the internal pull-up, so no external resistor is needed.

## Important: where Ollama runs

**A Pi Zero cannot run an LLM locally** - it doesn't have the RAM or CPU for
it. Run Ollama on another machine on the same network (a desktop, laptop, or
a beefier Pi) and point `OLLAMA_HOST` at it, e.g.:

```bash
# on the machine that will run the model:
ollama serve
ollama pull llama3.2
```

```bash
# in soccerball8/.env on the Pi:
OLLAMA_HOST=http://192.168.1.50:11434
```

The Pi Zero itself only needs to record audio, hit the network for
speech-to-text/search/Ollama, and push pixels to the little screen - all
lightweight.

## Software setup

```bash
sudo apt update
sudo apt install -y python3-venv portaudio19-dev libatlas-base-dev

git clone <this repo> ~/soccerball8 && cd ~/soccerball8
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-pi.txt   # gpiozero, RPi.GPIO, luma.lcd - Pi only

cp .env.example .env
nano .env   # set OLLAMA_HOST, GOOGLE_API_KEY, GOOGLE_CSE_ID, DISPLAY_DRIVER=st7789 (or ili9341)
```

Find your mic's device index if the default doesn't work:

```bash
python -m soccerball8.audio
```

Run it:

```bash
set -a; source .env; set +a
python -m soccerball8.main
```

### Google Custom Search API

1. Create a Programmable Search Engine at
   https://programmablesearchengine.google.com/ set to "Search the entire
   web" -> copy its Search engine ID into `GOOGLE_CSE_ID`.
2. Create an API key with the "Custom Search API" enabled at
   https://console.cloud.google.com/apis/credentials -> `GOOGLE_API_KEY`.

### Run on boot

```bash
sudo cp systemd/soccerball8.service /etc/systemd/system/
sudo nano /etc/systemd/system/soccerball8.service   # fix paths/user if needed
sudo systemctl daemon-reload
sudo systemctl enable --now soccerball8.service
```

## Developing off the Pi

Set `DISPLAY_DRIVER=dummy` (the default) and `pip install -r
requirements-dev.txt` for a `pygame` preview window instead of real SPI
hardware. The button trigger also falls back to pressing Enter when
`gpiozero`/GPIO isn't available.

## Project layout

```
soccerball8/
  audio.py          mic capture + speech-to-text (Google Web Speech API)
  ollama_client.py  thin HTTP client for a networked Ollama server
  search.py         Google Custom Search JSON API wrapper
  fact_check.py     cross-checks a claim against multiple search results
  answer_engine.py  question -> claim -> fact-check -> phrased answer
  animation.py      ball-approach / hexagon-zoom / typewriter frame generator
  display.py        SPI (ST7789/ILI9341) driver + dummy/pygame simulator
  main.py           button -> listen -> think -> animate loop
tests/
  test_fact_check.py
systemd/soccerball8.service
```

## Tests

The fact-checking logic is pure Python and network-free to test:

```bash
pip install -r requirements-dev.txt
pytest
```
