# AGENTS.md

Guidance for coding agents working in this repository. See
[README.md](README.md) for what the bridge is, the wiring, and the setup steps.

## What this is

ESP32-S3 firmware that talks to a Mitsubishi Ecodan heat pump over its CN105
service port. It's built on the esp-at firmware (submodule). Config is over
BLE (PIN required) and USB serial. The CN105 link is reachable over BLE or the
local network. There's no ESP-NOW.

The CN105 protocol is Mitsubishi's own, not Modbus. A Modbus interface would
need an adapter on the heat pump side (Mitsubishi A1M / A1M+, or Procon
MelcoBEMS Mini), or a Modbus layer on top of this board. Neither is decided.

## Layout

- `esp-at/`: git submodule, [aardbeiplantje/esp-at](https://github.com/aardbeiplantje/esp-at),
  branch `ecodan` (the pinned commit is there). The firmware base. Its sketch
  is `esp-at/esp-at/esp-at.ino`. Clone with `--recurse-submodules`, or run
  `git submodule update --init`.
- The Ecodan CN105 logic goes in esp-at's plugin hooks (`plugins.cpp`) in the
  fork. Keep changes to upstream esp-at files small, and commit them in the fork.
- `deploy.py`: build / flash / monitor tool. The `ECODAN` role builds the
  submodule sketch (`SKETCHES` in `deploy.py`).
- `boards.toml`: physical boards (MAC, chip, role `ECODAN`).
- `docs/gen_schematics.py`: generates `docs/ecodan.svg`, the wiring schematic.
- `README.md`: wiring, pin table, serial settings, setup steps.

## Build and check

There is no test suite and no hardware in CI. The minimum check for any
firmware change is a clean compile of every chip in `boards.toml`:

```sh
python3 deploy.py build all
```

`boards.toml` has only `esp32s3` boards right now. `esp32c3` must still
compile, so check it directly when you change the firmware:

```sh
arduino-cli compile -b esp32:esp32:esp32c3 --build-property \
  "build.extra_flags=-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1 -D_ARDUINO_BLE_H_" \
  --board-options PartitionScheme=no_ota --build-path /tmp/c3 esp-at/esp-at
```

`deploy.py` uses `$ARDUINO_DIRECTORIES_DATA`, else `./.arduino15` if it exists,
else arduino-cli's default. If the ESP32 core is installed elsewhere, point at
it:

```sh
ARDUINO_DIRECTORIES_DATA=$HOME/.arduino15 python3 deploy.py build all
```

A build can leave an untracked `esp-at/esp-at/build/` inside the submodule.
Delete it before committing the submodule.

The schematic is generated, never hand-edited. After changing
`docs/gen_schematics.py`, regenerate it and look at the result:

```sh
python3 docs/gen_schematics.py docs
rsvg-convert docs/ecodan.svg -o /tmp/ecodan.png
```

Don't flash boards unless asked: `deploy.py flash/deploy` writes to whatever
board in `boards.toml` is plugged in.

Target: Espressif Arduino core 3.3.x (`deploy.py` pins 3.3.12), `no_ota`
partitions, USB CDC on boot.

## Network and access

- BLE: the NUS service with AT commands. It's off until a 6-digit PIN is set
  with `AT+BLE_PIN`, and the security mode can't be set to 0. A PIN of
  `000000` is refused. The PIN is set on the device, never in the repo.
- The CN105 bridge runs over BLE (`AT+BLE_UART1`) or the TCP server
  (`AT+TCP_SERVER_START`). Only local clients are accepted: loopback, RFC1918,
  link-local and IPv6 ULA. Don't forward the TCP port on the router.
- WiFi credentials are set on the device with AT commands, not in the repo.

## Things that must stay in sync

- **Pins and serial settings:** the UART1 pins and the `AT+UART1=` line are in
  `README.md` and the schematic generator. Change all three together. The
  defaults for these are in esp-at (`UART1_RX_PIN` / `UART1_TX_PIN`).
- **Wiring:** a pin change means regenerating `docs/ecodan.svg` and updating
  the table in `README.md`.
- **Defaults and behaviour:** anything a user sees (AT commands, BLE PIN rules,
  TCP access) is documented in `README.md`. Update it with the code.
- **esp-at changes:** a fix to upstream esp-at is committed in the fork
  (branch `ecodan`), then the submodule pointer is updated here. The commit
  message names the fork commit.

## Hardware rules (proposed, confirm before relaxing)

The heat pump is mains equipment and its service port is not isolated from its
controller.

- The ESP32 GPIOs are 3.3 V only. Each CN105 signal goes through a PC817
  optocoupler, and the ESP side gets its own isolated 5 V. Never connect a
  CN105 pin directly to a GPIO.
- The ESP side's GND must stay separate from the heat pump GND. Powering the
  ESP from the CN105 +5 V pin or leaving USB connected while the heat pump is
  attached removes that isolation, so note it in any change to power or USB.
- Connect the board to the heat pump only through the CN105 connector. Don't
  tie the heat pump's ground to mains earth, or to any other ground on the
  board's side, without an isolation plan.
- Read-only by default. Anything that writes settings to the heat pump
  (setpoints, mode, on/off) is off until explicitly enabled. It must be
  rate-limited and bounded to safe ranges in firmware, not only in a UI.
- Outputs and writes default to off at boot. A reset must never command the
  heat pump.

## Code style

For this repo's own code (`deploy.py`, `docs/gen_schematics.py`, and the
Ecodan logic once it exists in the fork). esp-at's own style stays as it is.

- Python: 4-space indent, `snake_case`, and an argparse CLI like `deploy.py`.
- C++ (Ecodan logic in the fork): Arduino style, 4-space indent, `snake_case`
  functions and variables, `UPPER_CASE` defines, short `/* ---- section ---- */`
  headers.
- No dynamic allocation in the main loop. Use fixed-size buffers and `snprintf`
  for text output.
- Time-based code uses `millis()` with wrap-safe comparisons
  (`(int32_t)(now - t)`).
- Parse the UART frames from a buffer in the main loop. Keep interrupt or
  callback code minimal, and hand data to the loop through a buffer.

## Git

- This repo's branch is `master`, pushed to `origin`
  (`git@github.com:CowboyTim/mel-esp32.git`).
- Keep commits focused. Describe the hardware impact (pins, serial settings,
  anything that writes to the heat pump, BLE or network access) in the message.
- Don't commit build output (`dist/`, `.build/`, `build/`, `.arduino15/`,
  `esp-at/esp-at/build/`).
