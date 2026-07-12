# RuuviTagMonitor

## Purpose

Python/Tkinter desktop app for discovering nearby RuuviTag BLE advertisements and showing live environmental readings.

## Current Status

- Primary implementation is now Python/Tkinter, matching the user's earlier Python desktop apps.
- Uses `bleak` to receive BLE advertisements.
- Decodes Ruuvi RAWv2 manufacturer payloads (`0x0499`, data format `0x05`).
- Main UI shows sensor cards with temperature, humidity, pressure, battery, TX power, movement, sequence, RSSI, and last-seen time.
- Start, stop, and clear commands are exposed in the toolbar.
- Sensor card names are editable and persist by MAC address in `%LOCALAPPDATA%\RuuviTagMonitor\tag-names.json`.
- The app window automatically resizes around the detected sensor count, bounded by the active display work area.
- Each tag can independently log readings to its own CSV file at a configurable capture interval.
- Data collection settings persist by MAC address in `%LOCALAPPDATA%\RuuviTagMonitor\data-collection.json`; CSV files use the user-defined tag name and capture-start date and are stored in the adjacent `data` folder.
- A capture session keeps its initial filename across app restarts. Disabling and re-enabling collection starts a new file, with a numeric suffix when the same tag name and date already exist.
- The Generate temperature graphs command combines valid CSV readings by MAC address and opens a content-aware window that scales its graph panels to the tag count, using scrolling only when the content exceeds the available screen height.
- README screenshots are stored at `docs\ruuvitag-monitor.png` for the live monitor and `docs\ruuvitag-temperature-graphs.png` for the graph window.

## Build And Run

```powershell
cd C:\Coding\RuuviTagMonitor
.\.venv\Scripts\pythonw.exe main.py
```

Install dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Build EXE

Use `.\build_exe.ps1` to build a PyInstaller executable at `dist\RuuviTagMonitor.exe`.

- Last verified PyInstaller build size: about 42.2 MB (includes Matplotlib and its plotting dependencies).
- Verified launch path: `C:\Coding\RuuviTagMonitor\dist\RuuviTagMonitor.exe`.

## Notes

- The local PC Bluetooth adapter was confirmed to receive RuuviTag packets after installing the Realtek Bluetooth driver.
- This project is intentionally Python-first for smaller/familiar local build-and-run loops.
- Previous WinUI/.NET implementation files were removed; the repository now contains only the Python app path.
- Future useful step: add alert thresholds.
