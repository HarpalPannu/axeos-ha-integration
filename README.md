# AxeOS Home Assistant Integration

A custom Home Assistant integration for monitoring and controlling [Bitaxe](https://github.com/skot/bitaxe) Bitcoin miners running AxeOS.

> [!CAUTION]
> This is a **personal project** and is provided as-is. It comes with **no warranty** and **no responsibility** for any issues, data loss, or damage to your devices. Use at your own risk.

Installable via [HACS](https://hacs.xyz/) as a custom repository.

## Features

### Sensors
| Sensor | Unit | Description |
|--------|------|-------------|
| Current Hashrate | GH/s | Live mining hashrate |
| Power | W | Current power draw |
| ASIC Temperature | °C | ASIC chip temperature |
| VRM Temperature | °C | Voltage regulator temperature |
| ASIC Frequency | MHz | Current ASIC clock speed |
| Shares Accepted | count | Total accepted shares (since boot) |
| Shares Rejected | count | Total rejected shares (since boot) |
| Best Share | — | Highest difficulty share (all time) |
| Best Session Share | — | Highest difficulty share (this session) |
| Energy | kWh | Accumulated energy consumption (persists across HA restarts) |
| Boot Time | timestamp | When the device last started |
| Uptime Percentage | % | Monthly availability (resets each month) |
| WiFi RSSI | dBm | Wireless signal strength (diagnostic) |
| Fan RPM | RPM | Current fan speed (diagnostic) |
| Fan Mode | — | Current fan control mode (Auto or Manual, diagnostic) |

### Controls
| Entity | Type | Description |
|--------|------|-------------|
| Fan | Fan | Set fan speed (0–100%) with Auto/Manual preset modes |
| Target Temperature | Number | Set target ASIC temperature (30–90 °C) |
| Screen Sleep | Switch | Turn the OLED display on/off |
| Turn Off LED | Switch | Turn the onboard LED on/off |

### Binary Sensors
| Sensor | Description |
|--------|-------------|
| Online | Shows if the Bitaxe is reachable |

## Installation

### HACS (Recommended)
1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/HarpalPannu/axeos-ha-integration` as an **Integration**
4. Search for "AxeOS" and install
5. Restart Home Assistant

### Manual
1. Copy the `custom_components/axeos` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **AxeOS**
3. Enter a friendly name, the device IP/URL (e.g. `http://192.168.1.50`), and polling interval
4. Click Submit — the integration will test the connection before saving

## Configuration

After setup, click **Configure** on the integration card to change:
- **Host URL** — device IP or hostname
- **Update Interval** — polling frequency in seconds (default: 30)

## API Reference

This integration uses the [AxeOS REST API](https://osmu.wiki/bitaxe/api/):
- `GET /api/system/info` — read device telemetry
- `PATCH /api/system` — send configuration changes

## License

MIT
