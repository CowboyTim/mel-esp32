#!/usr/bin/env python3
"""Generate the wiring schematic in docs/ as SVG.

  python3 docs/gen_schematics.py docs

Writes docs/ecodan.svg. Don't edit the SVG by hand: change this script and regenerate.
Pins, net names and the UART settings here must match README.md and the esp-at
UART1 defaults (AT+UART1=baud,data,parity,stop,rx,tx).

Design: CN105 (heat pump side) -> two PC817 optocouplers -> ESP32 (isolated side).
The ESP side gets its own 5 V from an isolated DC-DC, and its GND is separate from
the heat pump GND. Both signal paths are non-inverting, so no UART inversion is used.
"""

import os
import sys
from xml.sax.saxutils import escape

W, H = 1100, 800

INK = "#1d2330"
MUTED = "#5b6475"
HV = "#c2410c"      # heat pump +5 V
GND_HP = "#334155"  # heat pump GND
GND_ISO = "#6b21a8" # isolated GND (ESP side)
ISO5 = "#9333ea"    # isolated 5 V
LV = "#15803d"      # 3V3 (ESP side)
SIG = "#1d4ed8"     # signals
NC = "#9ca3af"
BOX = "#f8fafc"
BOX_EDGE = "#334155"

out = []


def add(s):
    out.append(s)


def text(x, y, s, size=13, anchor="start", weight="normal", fill=INK):
    add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{fill}">{escape(s)}</text>')


def line(x1, y1, x2, y2, colour=INK, width=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
        f'stroke-width="{width}"{d}/>')


def dot(x, y, colour=INK):
    add(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{colour}"/>')


def box(x, y, w, h, title, sub=None, edge=BOX_EDGE):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{BOX}" '
        f'stroke="{edge}" stroke-width="2"/>')
    text(x + w / 2, y + 24, title, 15, "middle", "bold")
    if sub:
        text(x + w / 2, y + 42, sub, 11, "middle", "normal", MUTED)


def pin_in(x, y, label, anchor="start"):
    dx = 8 if anchor == "start" else -8
    text(x + dx, y + 4, label, 11, anchor, "normal", MUTED)


def opto_rect(x, y):
    add(f'<rect x="{x}" y="{y}" width="120" height="88" rx="6" fill="{BOX}" '
        f'stroke="{BOX_EDGE}" stroke-width="2"/>')


def opto_label(x, y, title, sub):
    text(x + 60, y + 44, title, 13, "middle", "bold")
    text(x + 60, y + 62, sub, 11, "middle", "normal", MUTED)


def stub_left(x, y, label, colour=INK, length=40):
    line(x, y, x - length, y, colour)
    dot(x, y, colour)
    text(x - length - 4, y + 4, label, 12, "end", "bold", colour)


def stub_right(x, y, label, colour=INK, length=40):
    line(x, y, x + length, y, colour)
    dot(x, y, colour)
    text(x + length + 4, y + 4, label, 12, "start", "bold", colour)


def gap_label(x1, x2, y, label, colour=INK, above=True):
    """Label centred in a wire gap."""
    text((x1 + x2) / 2, y - 6 if above else y + 16, label, 12, "middle", "bold", colour)


# Isolation barrier, drawn first so the boxes sit on top of it
add('<line x1="460" y1="200" x2="460" y2="460" stroke="#94a3b8" stroke-width="1.5" '
    'stroke-dasharray="6 5"/>')

# ---- heat pump side ---------------------------------------------------------------

CN_X, CN_W = 60, 180
CN_R = CN_X + CN_W              # 240
box(CN_X, 150, CN_W, 250, "CN105", "heat pump service port")
text(CN_X + CN_W / 2, 122, "heat pump side", 13, "middle", "bold", MUTED)
cn_pins = {170: ("1", NC), 210: ("2", GND_HP), 250: ("3", HV), 290: ("4", SIG), 370: ("5", SIG)}
for y, (num, c) in cn_pins.items():
    pin_in(CN_R, y, num, "end")
line(CN_R, 170, CN_R + 40, 170, NC, 2, "4 3")
text(CN_R + 44, 174, "not connected", 12, "start", "normal", NC)
dot(CN_R, 170, NC)
stub_right(CN_R, 210, "GND (HP)", GND_HP)
dot(CN_R, 250, HV)
dot(CN_R, 290, SIG)
dot(CN_R, 370, SIG)

# ---- optocouplers (straddle the isolation barrier) -------------------------------

OPT_X, OPT_W = 400, 120
OPT_R = OPT_X + OPT_W           # 520

# Opto A: HP TX -> ESP GPIO17 (RX). LED on the HP side, output on the ESP side.
opto_rect(OPT_X, 226)
pin_in(OPT_X, 250, "A", "start")
pin_in(OPT_X, 290, "K", "start")
pin_in(OPT_R, 250, "C", "end")
pin_in(OPT_R, 290, "E", "end")
opto_label(OPT_X, 226, "PC817 (A)", "RX path")

# Opto B: ESP GPIO18 (TX) -> HP RX. LED on the ESP side, output on the HP side.
opto_rect(OPT_X, 350)
pin_in(OPT_X, 370, "C", "start")
pin_in(OPT_X, 410, "E", "start")
pin_in(OPT_R, 370, "A", "end")
pin_in(OPT_R, 410, "K", "end")
opto_label(OPT_X, 350, "PC817 (B)", "TX path")

# Wires heat pump side -> opto inputs and outputs
line(CN_R, 250, OPT_X, 250, HV, 2)                    # +5 V into opto A LED (via 470R)
gap_label(CN_R, OPT_X, 250, "+5V (HP) via 470R", HV)
line(CN_R, 290, OPT_X, 290, SIG, 2)                   # TX into opto A LED
gap_label(CN_R, OPT_X, 290, "TX (HP out)", SIG, above=False)
line(CN_R, 370, OPT_X, 370, SIG, 2)                   # opto B output to HP RX
gap_label(CN_R, OPT_X, 370, "RX (HP in)", SIG)
text((CN_R + OPT_X) / 2, 392, "4k7 pull-up to +5V", 11, "middle", "normal", MUTED)
stub_left(OPT_X, 410, "GND (HP)", GND_HP)             # opto B emitter to HP GND

# ---- isolated side (ESP32) -----------------------------------------------------------

DC_X, DC_W = 560, 160
box(DC_X, 150, DC_W, 44, "isolated DC-DC", "5 V in, 5 V out", edge=ISO5)
stub_left(DC_X, 172, "+5V (HP)", HV)                  # DC-DC input from heat pump 5 V

ES_X, ES_W = 780, 200
ES_R = ES_X + ES_W
box(ES_X, 130, ES_W, 330, "ESP32-S3 SuperMini", "esp-at firmware", edge=GND_ISO)
text(ES_X + ES_W / 2, 480, "isolated side", 13, "middle", "bold", MUTED)
es_pins = {170: ("5V", ISO5), 250: ("GPIO17 RX", SIG), 290: ("GND", GND_ISO),
           370: ("3V3", LV), 410: ("GPIO18 TX", SIG)}
for y, (name, c) in es_pins.items():
    pin_in(ES_X, y, name, "start")

# DC-DC output to ESP 5 V pin
line(DC_X + DC_W, 172, ES_X, 170, ISO5, 2)
gap_label(DC_X + DC_W, ES_X, 170, "5V ISO", ISO5)

# Opto A output -> ESP GPIO17, with 10k pull-up to 3V3
line(OPT_R, 250, ES_X, 250, LV, 2)
gap_label(OPT_R, ES_X, 250, "RX to GPIO17", SIG)
text((OPT_R + ES_X) / 2, 266, "10k pull-up to 3V3", 11, "middle", "normal", MUTED)
# Opto A emitter -> isolated GND
line(OPT_R, 290, ES_X, 290, GND_ISO, 2)
gap_label(OPT_R, ES_X, 290, "GND (ISO)", GND_ISO, above=False)

# ESP 3V3 -> opto B LED via 330R; GPIO18 -> opto B LED cathode
line(ES_X, 370, OPT_R, 370, LV, 2)
gap_label(OPT_R, ES_X, 370, "3V3 via 330R", LV)
line(ES_X, 410, OPT_R, 410, SIG, 2)
gap_label(OPT_R, ES_X, 410, "TX from GPIO18", SIG, above=False)

# Isolation barrier, drawn through the opto centres
text(460, 196, "isolation barrier", 11, "middle", "normal", MUTED)

# ---- notes -------------------------------------------------------------------------

notes = [
    "Wiring (proposed, verify on hardware):",
    "- Each signal goes through a PC817 optocoupler. The ESP side has its own isolated 5 V and its GND is separate from the heat pump GND.",
    "- CN105 pin 1 not connected. Pin 2 GND, pin 3 +5V, pin 4 TX (heat pump out), pin 5 RX (heat pump in).",
    "- Both paths are non-inverting: keep UART inversion off (AT+UART1 inverted = 0).",
    "- Parts: 2x PC817 (6N137 if you need more speed); 470R LED (HP side); 330R LED (ESP side);",
    "  4k7 pull-up to +5V on the RX line (HP side); 10k pull-up to 3V3 on the GPIO17 line (ESP side);",
    "  isolated 5 V to 5 V DC-DC, 1 W or more.",
    "- UART on GPIO17 (RX) and GPIO18 (TX): AT+UART1=2400,8,1,1,17,18",
    "  (2400 baud, 8 data bits, even parity, 1 stop bit. Not checked against the Ecodan protocol.)",
    "- USB-C on the ESP side ties its GND to the PC. Don't plug USB in while the heat pump is connected, or use a USB isolator.",
    "- Check the heat pump's own pull-ups on TX/RX first. If they're already there, drop the 4k7.",
    "- No mains on this board.",
]
y0 = 530
add(f'<rect x="40" y="{y0 - 22}" width="{W - 80}" height="{len(notes) * 20 + 22}" rx="8" '
    f'fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>')
for i, n in enumerate(notes):
    text(60, y0 + i * 20, n, 13, "start", "bold" if i == 0 else "normal", INK if i == 0 else MUTED)


# ---- write -------------------------------------------------------------------------

def build():
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="Helvetica, Arial, sans-serif">')
    title = ('<text x="40" y="50" font-size="22" font-weight="bold" fill="#1d2330">'
             'Ecodan CN105 bridge: wiring</text>'
             '<text x="40" y="74" font-size="13" fill="#5b6475">'
             'esp-at on an ESP32-S3 SuperMini. Optocouplers on each line, isolated 5 V for the ESP side.</text>')
    bg = f'<rect width="{W}" height="{H}" fill="#ffffff"/>'
    return "\n".join([head, bg, title] + out + ["</svg>", ""])


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else "docs"
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, "ecodan.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build())
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
