# AGENTS.md

Guidance for coding agents working in this repository.

## What this is

ESP32 firmware that talks to a Mitsubishi Ecodan heat pump over its CN105 UART
port, built on the esp-at firmware (submodule). Config is over BLE (PIN
required), and the CN105 link is reachable over BLE or the local network. No
ESP-NOW.

The CN105 protocol is Mitsubishi's own, not Modbus. Modbus on the heat pump
side needs an adapter (Mitsubishi A1M / A1M+, or Procon MelcoBEMS Mini). If a
Modbus interface is wanted from this board, it's added on top of the bridge. See [README.md](README.md) for the current status; the
pin table, serial settings and the Modbus register map will live there once
written.

## Layout

- `esp-at/`: git submodule, [aardbeiplantje/esp-at](https://github.com/aardbeiplantje/esp-at).
  The firmware base: AT command set over UART and BLE (NUS), WiFi, local TCP
  server, UART1 bridge. Its sketch is `esp-at/esp-at/esp-at.ino`. Clone with
  `git clone --recurse-submodules`, or `git submodule update --init`.
- The Ecodan CN105 logic goes in the esp-at plugin hooks (`plugins.cpp`) and
  the esp-at fork. Keep changes to upstream files small and in the fork.
- `deploy.py`: build / flash / monitor tool. The `ECODAN` role builds the
  submodule sketch (`SKETCHES` in `deploy.py`).
- `boards.toml`: the physical boards (MAC, chip, role `ECODAN`).

## Build and check

There is no test suite and no hardware in CI. The minimum check for any
firmware change is a clean compile:

```sh
python3 deploy.py build all
```

`deploy.py` uses `$ARDUINO_DIRECTORIES_DATA`, else `./.arduino15` if it exists,
else arduino-cli's default. If the ESP32 core is installed elsewhere, point at
it:

```sh
ARDUINO_DIRECTORIES_DATA=$HOME/.arduino15 python3 deploy.py build all
```

Don't flash boards unless asked: `deploy.py flash/deploy` writes to whatever
board in `boards.toml` is plugged in.

Target: Espressif Arduino core 3.3.x, chip from `boards.toml` (`esp32s3` now,
`esp32c3` must keep compiling), `no_ota` partitions, USB CDC on boot. Code that
differs per chip goes under `#if CONFIG_IDF_TARGET_ESP32S3`. Use the core 3.x
APIs (`uartBegin`/`HardwareSerial` by pin, `ledcAttach`/`ledcWrite` by pin if
PWM is used).

## Network

- Config over BLE (NUS, AT commands). BLE is off until a 6-digit PIN is set
  with `AT+BLE_PIN`, and the security mode can't be set to 0. A PIN of
  `000000` is refused. The PIN is set on the device, never in the repo.
- The UART1 bridge (CN105) goes over BLE (`AT+BLE_UART1`) or the local TCP
  server. Only local clients are accepted: loopback, RFC1918, link-local and
  IPv6 ULA. Don't forward the TCP port on the router.
- WiFi credentials are set on the device with AT commands, not in the repo.
- Modbus is not decided. If it's added it's a plugin on top of the bridge.

## Things that must stay in sync

- **Pin assignments:** a pin change touches the `#define`s in `main.cpp` and
  the pin table in `README.md`.
- **Serial settings:** baud rate, parity and stop bits for the heat pump link
  live in one place in `main.cpp` and are noted in `README.md`.
- **esp-at changes:** a fix to upstream esp-at is made in the fork, then the
  submodule pointer is updated here. Note the commit in the message.
- **Defaults and behaviour:** settings defaults and anything a user can see
  (LED patterns, web UI, MQTT topics or similar) are documented in `README.md`;
  update it with the code.

## Hardware rules (proposed, confirm before relaxing)

The heat pump is mains equipment and its service port is not isolated from its
controller. Keep these in the esp-at fork's Ecodan code:

- The ESP32 GPIOs are 3.3 V only. Level-shift the heat pump's serial line
  and never connect it to a pin directly.
- Connect the board to the heat pump's serial port through its documented
  connector only. Don't tie the heat pump's ground to mains earth or to any
  other ground on the board's side without an isolation plan.
- Read-only by default. Anything that writes settings to the heat pump
  (setpoints, mode, on/off) is off until explicitly enabled, and must be
  rate-limited and bounded to safe ranges in firmware, not only in the UI.
- Outputs and writes default to off at boot; a reset must never command the
  heat pump.

## Code style

- C++ in Arduino style, 4-space indent, `snake_case` functions and
  variables, `UPPER_CASE` defines, short `/* ---- section ---- */` headers.
- No dynamic allocation in the main loop; fixed-size buffers and `snprintf`
  for any text output.
- Everything time-based uses `millis()` with wrap-safe comparisons
  (`elapsed()` / `(int32_t)(now - t)`).
- Parse the UART frames in `loop()` from a buffer. Keep interrupt or callback
  code minimal, and copy data into a buffer that `loop()` handles.

## Git

- Default branch is `main`. Keep commits focused and describe the hardware
  impact (pins, serial settings, anything that writes to the heat pump) in
  the message.
- Don't commit build output (`dist/`, `.build/`, `build/`, `.arduino15/`).
