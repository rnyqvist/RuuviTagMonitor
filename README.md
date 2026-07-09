# RuuviTag Monitor

Python/Tkinter desktop app for discovering nearby RuuviTag BLE advertisements and showing live sensor values.

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
