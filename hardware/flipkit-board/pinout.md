# FlipKit Custom Board — CM5 Pin Assignment

## SPI0 — RFID (MFRC522)
| CM5 Pin | GPIO | Signal    |
|---------|------|-----------|
| 23      | 11   | SPI0_SCLK |
| 21      | 9    | SPI0_MISO |
| 19      | 10   | SPI0_MOSI |
| 24      | 8    | SPI0_CE0  |
| 22      | 25   | MFRC522_RST |

## SPI1 — Sub-GHz (CC1101)
| CM5 Pin | GPIO | Signal    |
|---------|------|-----------|
| 40      | 21   | SPI1_SCLK |
| 35      | 19   | SPI1_MISO |
| 38      | 20   | SPI1_MOSI |
| 26      | 7    | SPI1_CE1  |
| 15      | 22   | CC1101_GDO0 |
| 11      | 17   | CC1101_GDO2 |

## I2C0 — Onboard peripherals
| CM5 Pin | GPIO | Signal  |
|---------|------|---------|
| 27      | 0    | I2C0_SDA |
| 28      | 1    | I2C0_SCL |

## GPIO — IR / LEDs / Control
| CM5 Pin | GPIO | Signal       |
|---------|------|--------------|
| 11      | 17   | IR_TX (via Q1 MOSFET) |
| 12      | 18   | IR_RX (TSOP4838) |
| 29      | 5    | LED_RFID     |
| 31      | 6    | LED_RF       |
| 33      | 13   | LED_ACT      |

## USB
| Signal       | Destination          |
|--------------|----------------------|
| CM5 USB2_DP/DM | CH334R hub input   |
| Hub port 0   | J2 USB-C OTG/BadUSB  |
| Hub port 1   | J3 USB-A host        |
| Hub port 2–3 | Internal (reserved)  |

## Camera / Display
| Signal    | Connector |
|-----------|-----------|
| CAM0_DATA | J4 CSI FFC 22-pin |
| DSI0      | J5 DSI FFC 22-pin |
| HDMI0     | J6 Micro HDMI     |

## Power Rails
| Rail  | Source      | Load                        |
|-------|-------------|-----------------------------|
| VBAT  | JST LiPo    | BQ25895 input               |
| 5V    | BQ25895 boost | CM5 VCC, USB hub, IR LED  |
| 3.3V  | TPS62085    | MFRC522, CC1101, logic      |
| 1.8V  | TPS62085    | CM5 IO banks (1V8 domain)   |
