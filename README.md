# RuuviTag Monitor

Python/Tkinter desktop app for discovering nearby RuuviTag BLE advertisements and showing live sensor values.

![RuuviTag Monitor screenshot](docs/ruuvitag-monitor.png)

## Hardware Requirements

- Windows PC with a Bluetooth adapter that supports Bluetooth Low Energy (BLE).
- BLE advertisement scanning support is required; pairing the RuuviTags is not needed.
- RuuviTags must be awake, broadcasting, and within Bluetooth range of the PC.
- Use the vendor Bluetooth driver when possible. On the development PC, the Realtek Bluetooth driver was required for reliable RuuviTag packet reception.
- If scans show no tags, check Windows Bluetooth is enabled, the Bluetooth Support Service is running, and no driver/device error is shown in Device Manager.

## Run

```powershell
cd C:\Coding\RuuviTagMonitor
.\.venv\Scripts\pythonw.exe main.py
```

If the virtual environment does not exist yet:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\pythonw.exe main.py
```

## Features

- Start/stop BLE scanning.
- Decode Ruuvi RAWv2 manufacturer packets.
- Show temperature, humidity, pressure, battery, TX power, movement, sequence, RSSI, and last-seen time.
- Rename tags inline.
- Remember tag names by MAC address in `%LOCALAPPDATA%\RuuviTagMonitor\tag-names.json`.
- Auto-resize the window around the detected tag count.

## Shortcuts

- `F5`: start scanning.
- `Esc`: stop scanning.

## Build EXE

```powershell
.\build_exe.ps1
```
