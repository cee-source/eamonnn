# Soccer 8-Ball

A Magic 8-Ball for soccer fans, built on a Raspberry Pi Zero. Shake it, ask
your question out loud, and it "thinks" by cross-checking your question
against several independent Google search results using free keyword
heuristics (no AI/LLM, no server to run, no license to worry about), then
reveals its verdict on a small screen: a soccer ball flies at the camera,
one white hexagon panel keeps zooming in until it fills the whole screen,
and the answer types itself on over the white.

If the search results don't clearly agree with each other, it says **"I
don't know"** instead of guessing. A small LED lights up when the power
bank is running low: an INA219 voltage sensor spliced into the power line
gives an early warning before things get bad, or if you skip that part, it
falls back automatically to the Pi's own under-voltage detection instead.

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

## Shopping list

**This build is 100% solderless** - no soldering iron needed anywhere.
That's a deliberate choice, not a workaround: it comes from buying a Pi
variant with the GPIO header already attached at the factory, and using a
breadboard + plug-in jumper wires instead of a perma-proto board. See
"Going solderless" below for how the connections still hold up to being
shaken.

**A note on the prices below:** Amazon blocks automated price scraping and
its search results don't reliably surface live prices, so these are ranges
compiled from current listings and typical market rates for these
component categories, not a guaranteed checkout total - sellers, stock, and
"scarcity" markups (especially on the Pi itself) shift week to week. Click
through and check the current price before ordering.

### Per unit

| Qty | Item | Amazon (approx.) | Notes |
|-----|------|-------------------|-------|
| 1 | Raspberry Pi Zero 2 WH (**"WH"**, with the GPIO header pre-soldered at the factory) | **$20-$45** | [Example listing](https://www.amazon.com/Raspberry-Pi-Zero-2-WH/dp/B0DB2JBD9C). Get the "WH" version specifically, not plain "W" - the plain version ships with bare, unpopulated header holes that you'd otherwise have to solder pins onto yourself. Needs Wi-Fi for Google Search + speech-to-text. |
| 1 | microSD card, 32GB A1-rated (e.g. SanDisk Ultra) | **$7-$12** | [Example listing](https://www.amazon.com/SanDisk-Ultra-microSDHC-Memory-Adapter/dp/B08GY9NYRM). Raspberry Pi OS Lite - no desktop needed, the screen is driven directly over SPI. |
| 1 | 2.4"-2.5" SPI TFT display, ST7789V or ILI9341, 240x320 | **$9-$16** | [Example listing](https://www.amazon.com/display-240x320-interface-driver-ST7789V/dp/B0C3BGPZQY). Confirm it's SPI (4-wire), not parallel/DPI, and that it lists pre-soldered header pins (virtually all of these do). |
| 1 | Mini USB microphone | **$8-$16** | [Example listing](https://www.amazon.com/Adafruit-Mini-USB-Microphone-ADA3367/dp/B071YMZQP1). Needs USB-A. |
| 1 (pack) | Micro-USB OTG adapter (USB-A female to Micro-USB male) | **$6-$9** for a 2-3 pack | [Example listing](https://www.amazon.com/CableCreation-Female-Assorted-Direction-Straight/dp/B013G4DMCE). Only need one, but these are sold in multi-packs. Skip if using a full-size-USB Pi variant. |
| 1 (pack) | MPU6050 accelerometer/gyroscope breakout (GY-521) | **$7-$10** single, or **~$2-3/unit** in a 5-10 pack | [Example listing](https://www.amazon.com/HiLetgo-MPU-6050-Accelerometer-Gyroscope-Converter/dp/B078SS8NQV). The shake sensor - comes with pins pre-soldered. Buy a multi-pack if building more than one or two units. |
| 1 (kit) | 5mm LED assortment kit | **$8-$12** | [Example listing](https://www.amazon.com/DiCUNO-450pcs-Colors-Emitting-Assorted/dp/B073QMYKDM). Only 1 LED needed per unit - the rest are spares for the whole run. |
| 1 (kit) | Resistor assortment kit (need ~330 ohm) | **$7-$10** | Often bundled with LED kits above - check before buying separately. |
| 1 (optional) | INA219 voltage/current sensor breakout | **$7-$12** | [Example listing](https://www.amazon.com/HiLetgo-INA219-Bi-Directional-Current-Breakout/dp/B07VL8NY32). Gives an early low-power warning instead of waiting for the Pi's own under-voltage protection. The one part of this build that involves cutting a wire (see "Going solderless" below) - **skip it entirely if that's unwanted**; everything falls back automatically to the free, zero-wiring method without it. |
| 1 | Mini solderless breadboard (400 tie-points) | **$3-$8** (often sold in multi-packs of 3-6, ~$1-2 each) | [Example listing](https://www.amazon.com/HiLetgo-Solderless-Breadboard-Circuit-Prototyping/dp/B00LSG5BJK). Where the accelerometer/LED/INA219 all plug in - replaces the perma-proto board, no soldering. |
| 1 (pack) | Female-to-female jumper wires (dupont-style, 40-pack) | **$6-$9** | [Example listing](https://www.amazon.com/Female-Dupont-Jumper-Wires-Cable/dp/B00RLQE3E0). Every connection in this build is one of these - Pi GPIO pins are male, and every module's header pins are male too, so female-to-female is what you need throughout. |
| 1 (optional) | Mini hot glue gun kit | **$10-$18** | [Example listing](https://www.amazon.com/Gorilla-8401509-Hot-Glue-Sticks/dp/B07K791YRP). A dab over each jumper-wire connector is what keeps friction-fit wiring from working loose under repeated shaking - see "Going solderless" below. Low-heat craft tool, not a soldering iron. |
| 1 | Small USB power bank, 5000mAh+, 5V/2A+ output | **$15-$25** | See "Choosing the power bank" below - not every power bank works for an always-on device like this one. |
| 1 | Inline micro-USB power switch (ready-made cable, nothing to assemble) | **$6-$9** | [Example listing](https://www.amazon.com/LoveRPi-MicroUSB-Switch-Raspberry-Female/dp/B018BFWLRU). This is a complete cable with the switch already built in - you just plug it in, no wiring involved. Lets you fully cut power between uses - the single biggest lever on battery life. |
| 1 | Enclosure/case | **$6-$15** | 3D-print filament cost, or an off-the-shelf project box, sized/weighted so it feels good to shake, with room for the power bank and breadboard. |
| - | M2.5 standoffs/screws (optional, kit) | **$7-$10** | For mounting the Pi and display inside the case. |

**Buying one of everything above at listed prices: ~$115-$220** (add
$7-$12 more if you include the optional INA219). That's the honest total
for building your *first* unit, because several of these are sold as kits
or multi-packs (the jumper wire pack, breadboards, LED/resistor
assortments, standoffs, and bulk MPU6050 packs) - you'll have leftover
material for several more units afterward. Once those shared kits are
bought, each *additional* unit mainly costs the Pi, microSD, display, mic,
power bank, and enclosure - roughly **$65-$115** each after the first.

### Going solderless

Two changes make the whole build solder-free, and one part needs a small
extra step if you want it:

- **Buy the Pi with headers already attached.** The plain "Raspberry Pi
  Zero 2 W" ships with bare, unpopulated holes where the 40-pin GPIO header
  would go - normally the first thing you'd solder yourself. The **"WH"**
  version (sometimes sold as "Zero 2 WH" or in a "kit" bundle) has that
  header pre-soldered at the factory. Every sensor/display module in this
  list already ships with its own pins pre-soldered too (that's the
  standard way these breakout boards are sold) - so once the Pi itself has
  a header, *nothing* in the whole build requires you to pick up an iron.
- **Use a breadboard instead of a perma-proto board.** Every connection
  becomes a female-to-female jumper wire pushed onto a pin - the
  accelerometer, LED, and (optional) INA219 all plug into the breadboard,
  and the breadboard's shared power rails mean you only need one jumper
  from the Pi's 3V3 pin and one from GND, rather than wiring each module's
  power pins back to the Pi individually.
- **Reliability under shaking:** friction-fit connections are more prone to
  working loose than a soldered joint, which matters here since the whole
  point is a device that gets shaken. Two fixes, neither of which needs
  heat beyond a low-temp glue gun: (1) stick the breadboard down firmly
  inside the case - most already have self-adhesive backing - so it can't
  shift, and (2) once everything is wired and tested, put a small dab of
  hot glue over each jumper wire where it plugs into a pin. That locks the
  connection in place without desoldering ever being a possibility if you
  need to change something later (a soldered joint would be harder to
  undo). Zip-tie or tape the wire bundle too, so shaking stresses the tie,
  not the connectors.
- **The one exception: the optional INA219.** Wiring it in means cutting
  the power bank's +5V wire and joining the two ends to the sensor's
  VIN+/VIN- pins. That's still solderless - solderless crimp butt
  connectors (a squeeze tool, no heat or fumes, [example
  listing](https://www.amazon.com/Wirefy-Non-Insulated-Butt-Connectors/dp/B08BYXJ2QQ))
  do the job - but it is the one place you're physically joining wires
  rather than just plugging things in. If that's not something you want to
  take on, **skip the INA219 entirely** - the device still gets a low-power
  warning for free from the Pi's own detection, with zero wiring changes.

### Choosing the power bank

A wall-plug supply is the easy choice, but it isn't portable, so this needs
a battery bank instead - with two catches that are easy to miss:

- **Auto-shutoff.** Most cheap power banks cut their own output if they
  don't see enough current draw for a while (they're designed for phones,
  which draw a big charging current; a Pi Zero 2 W sitting idle between
  shakes draws maybe 150-250mA, well under many banks' 300-500mA cutoff
  threshold). A bank that shuts itself off mid-idle means the whole device
  randomly dies. Look for a bank explicitly marketed as supporting
  **low-current/small-device charging** (commonly advertised for
  smartwatches, fitness trackers, or wireless earbuds cases) - that's the
  spec that actually matters here, more than raw mAh.
- **Runtime vs. always-on.** At roughly 1-1.5W idle plus short spikes while
  thinking/animating, a 5000mAh bank gives on the order of half a day to a
  day of standby - fine for a gift/novelty item that gets picked up
  occasionally, but it'll drain if left "on" continuously. The inline power
  switch above is what makes this practical: flip it off when not in use,
  and shelf life stops being a battery question at all.

### Tools (one-time, shared across a whole production run)

No soldering iron on this list - see "Going solderless" above.

| Qty | Item | Amazon (approx.) | Notes |
|-----|------|-------------------|-------|
| 1 (optional) | Wire strippers/cutters | **$8-$15** | Only needed if you're doing the optional INA219 power splice; skip entirely otherwise. |
| 1 (optional) | Anti-static mat or wristband | **$10-$15** | Cheap insurance for the Pi Zero and sensor boards. |
| 1 | Digital multimeter | **$15-$30** | [Search results](https://www.amazon.com/digital-multimeter/s?k=digital+multimeter). For checking continuity/voltage before first power-on of each unit. |

**Total tools: ~$15-$30** if you skip the INA219 splice (just the
multimeter), or **~$23-$45** with wire strippers added for that optional
step, **~$33-$60** if you also want the anti-static mat. One-time purchase
- reuse across every unit you build, doesn't factor into the per-unit cost
above. (The hot glue gun from the per-unit table above is listed there
instead, since a full kit's worth of glue sticks realistically covers many
units.)

All the wiring below is female-to-female jumper wires, pushed directly onto
the Pi's GPIO header and onto each module's pre-soldered pins - see "Going
solderless" above. Route the accelerometer, LED, and INA219 through the
breadboard (its shared power rails mean one jumper from the Pi's 3V3 pin
and one from GND cover all three); the display's pins usually connect
straight to the Pi instead, since it doesn't share rails with anything.

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

### Wiring the accelerometer (I2C shake sensor)

| MPU6050 pin | Pi Zero pin       |
|-------------|-------------------|
| VCC         | 3V3               |
| GND         | GND               |
| SCL         | GPIO3 (I2C1 SCL)  |
| SDA         | GPIO2 (I2C1 SDA)  |

Enable I2C first: `sudo raspi-config` -> Interface Options -> I2C -> Enable.
Confirm it's wired correctly with `i2cdetect -y 1` - it should show a device
at address `0x68` (or `0x69` if the module's AD0 pin is tied high; set
`ACCELEROMETER_ADDRESS=0x69` in that case).

Shaking is tuned via four settings in `.env` - `SHAKE_THRESHOLD_G` (how hard
a swing has to be), `SHAKE_REQUIRED_SPIKES` and `SHAKE_WINDOW_SECONDS` (how
many swings, how quickly, before it counts as "shaken"), and
`SHAKE_COOLDOWN_SECONDS` (settle time before listening starts). The defaults
are a reasonable starting point - nudge `SHAKE_THRESHOLD_G` up if it's
triggering on being picked up gently, or down if a real shake isn't
registering.

### Wiring the low-power LED

| LED circuit          | Pi Zero pin |
|-----------------------|-------------|
| Resistor -> GPIO27 (configurable, `LOW_POWER_LED_GPIO_PIN`) | GPIO27 |
| LED cathode (short leg) | GND |

Wire it as `GPIO -> 330 ohm resistor -> LED anode`, `LED cathode -> GND`,
via the breadboard - plug the LED and resistor into the same row so they're
in series, no soldering needed. By default the light is driven by the Pi's
own power management chip,
which already detects when the 5V input rail sags - exactly what happens
as a power bank's battery runs low under load. The main loop polls this
every `LOW_POWER_POLL_SECONDS` (default 5s) and lights the LED for as long
as the under-voltage condition is active. This relies on the `vcgencmd`
tool, which ships with Raspberry Pi OS by default, and it's free - no extra
part needed.

### Wiring the INA219 (optional, for an earlier warning)

The Pi's own detection above only trips once the rail has already sagged
close to the point where the Pi could misbehave. An INA219 measures the
actual rail voltage directly, so it can warn well before that - the
trade-off is it means splicing into the power line:

| INA219 pin | Connects to |
|------------|-------------|
| VIN+       | Power bank / switch side of the 5V feed (cut the cable's +5V wire and land the bank-side end here) |
| VIN-       | Pi-side of the cut +5V wire (the module's internal shunt completes the circuit) |
| VCC        | Pi 3V3 |
| GND        | Pi GND |
| SCL        | GPIO3 (I2C1 SCL) - same bus as the accelerometer, different address |
| SDA        | GPIO2 (I2C1 SDA) - same bus as the accelerometer, different address |

The MPU6050 (`0x68`) and INA219 (default `0x40`) share the same I2C bus
without conflict since they're at different addresses - no need for a
second bus. Set `INA219_THRESHOLD_V` in `.env` to whatever margin you want
above the Pi's own ~4.63V cutoff (default 4.8V). If no INA219 answers on
the bus, `soccerball8/power_monitor.py` detects that automatically at
startup and falls back to the `vcgencmd`-only method above - no
configuration change needed either way.

## Software setup

```bash
sudo apt update
sudo apt install -y python3-venv portaudio19-dev libatlas-base-dev

git clone <this repo> ~/soccerball8 && cd ~/soccerball8
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-pi.txt   # smbus2, RPi.GPIO, luma.lcd - Pi only

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
hardware. The shake trigger also falls back to pressing Enter when
`smbus2`/an accelerometer isn't available.

## Project layout

```
soccerball8/
  shake.py          MPU6050 accelerometer driver + shake-to-ask detection
  power_monitor.py  low-power warning LED (INA219 if present, else Pi under-voltage detection)
  ina219.py         minimal read-only INA219 driver (bus voltage only)
  audio.py          mic capture + speech-to-text (Google Web Speech API)
  search.py         Google Custom Search JSON API wrapper
  fact_check.py     cross-checks a question against multiple search results
  answer_engine.py  fact-check verdict -> phrased Magic-8-Ball answer
  animation.py      ball-approach / hexagon-zoom / typewriter frame generator
  display.py        SPI (ST7789/ILI9341) driver + dummy/pygame simulator
  main.py           shake -> listen -> think -> animate loop
tests/
  test_fact_check.py
  test_shake.py
  test_power_monitor.py
systemd/soccerball8.service
```

## Tests

The fact-checking logic is pure Python and network-free to test:

```bash
pip install -r requirements-dev.txt
pytest
```
