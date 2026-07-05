# Soccer 8-Ball

A Magic 8-Ball for soccer fans, built on a Raspberry Pi Zero. Ask it a
question out loud; it "thinks" by cross-checking your question against
several independent Google search results using free keyword heuristics (no
AI/LLM, no server to run, no license to worry about), then reveals its
verdict on a small screen: a soccer ball flies at the camera, one white
hexagon panel keeps zooming in until it fills the whole screen, and the
answer types itself on over the white.

If the search results don't clearly agree with each other, it says **"I
don't know"** instead of guessing.

## How the "is this actually true" check works

1. `soccerball8/search.py` fetches several independent results from Google
   Custom Search for your question.
2. `soccerball8/fact_check.py` classifies each result snippet as `SUPPORTS`,
   `CONTRADICTS`, or `UNRELATED` by checking how many of the question's
   keywords it contains, and whether it also contains a negation word
   ("not", "never", "debunked", ...). Then it:
   - takes the fraction of relevant results that agree (the "stance
     probability"),
   - separately measures how much the supporting/contradicting snippets
     textually corroborate **each other** (independent of the question), so
     one outlier result can't dominate the vote,
   - blends both into one confidence score.
3. If there isn't enough relevant evidence, or confidence falls below
   `CONFIDENCE_THRESHOLD` (default 0.7), the answer is **"I don't know"**.
   Otherwise a short Magic-8-Ball-style line is picked from a canned phrase
   bank based on the verdict.

This is deliberately rule-based rather than LLM-based: it's free forever,
there's no per-unit API key or server for a customer to set up, and nothing
to license for resale. The trade-off is it's less clever than an LLM at
parsing oddly-phrased questions - straightforward yes/no factual questions
("did Messi win the World Cup") work well; vague or very colloquial phrasing
may land on "I don't know" more often.

## Shopping list (per unit)

| Qty | Item | Notes |
|-----|------|-------|
| 1 | Raspberry Pi Zero 2 W | Needs Wi-Fi for Google Search + speech-to-text. The Zero 2 W is strongly recommended over the original Zero/Zero W - noticeably faster for the animation loop and network calls, similar price. |
| 1 | microSD card, 8GB+ (A1-rated) | Raspberry Pi OS Lite (no desktop needed - the screen is driven directly over SPI) |
| 1 | 2.4"-2.5" SPI TFT display, ST7789V or ILI9341, 240x320 | e.g. "Waveshare 2.4inch LCD Module" or generic "2.4 inch SPI TFT ST7789" listings. Confirm it's SPI (4-wire), not parallel/DPI. |
| 1 | Mini USB microphone | A small USB lavalier/desktop mic, e.g. generic "mini USB microphone" listings. Needs USB-A. |
| 1 | Micro-USB OTG adapter (USB-A female to Micro-USB male) | To plug the USB mic into the Pi Zero's data port. Not needed if using a Zero 2 W's full-size USB port variant. |
| 1 | Momentary push button (6mm or 12mm) | The "ask a question" trigger |
| 2 | Jumper wires, female-to-female | Button to GPIO + GND |
| 1 | 5V/2.5A micro-USB power supply | Official Raspberry Pi power supply recommended for stability |
| 1 | Enclosure/case | 3D-printed or off-the-shelf project box with cutouts for the screen, mic, button, and a soccer-ball-themed shell if you want the physical look to match the on-screen animation |
| 1 | Perma-proto board or small breadboard (optional) | For a clean solder-down of the button + display headers instead of loose jumpers |
| - | M2.5 standoffs/screws (optional) | For mounting the Pi and display inside the case |

Approximate per-unit hardware cost: **$25-$40** depending on sourcing and
display choice, before enclosure/assembly labor.

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
nano .env   # set GOOGLE_API_KEY, GOOGLE_CSE_ID, DISPLAY_DRIVER=st7789 (or ili9341)
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

**Free tier caveat:** Google Custom Search gives **100 free queries/day per
API key**; each question this device asks uses one query. Beyond 100/day it
bills per additional query unless you raise the quota. If you're selling
many units, either have each unit use its own free API key (fine for light
personal use per household) or budget for overage if you expect heavy use.
When the quota is hit, the search call fails gracefully and the device just
answers **"I don't know"** rather than erroring out.

**Speech-to-text caveat:** transcription uses the free, unofficial Google
Web Speech endpoint (via the `SpeechRecognition` library) - free with no key
needed, but undocumented and rate-limited by Google, not something to rely
on for high call volume. For a small hobby/gift-shop batch this is fine; if
you scale up and start seeing failures, swapping in an offline recognizer
(e.g. `vosk`, which has small enough models to run - slowly - on a Pi Zero)
is the free alternative, at the cost of extra setup and CPU time.

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
  search.py         Google Custom Search JSON API wrapper
  fact_check.py     cross-checks a question against multiple search results
  answer_engine.py  fact-check verdict -> phrased Magic-8-Ball answer
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
