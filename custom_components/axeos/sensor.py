"""AxeOS sensor platform.

Provides the following sensor types:
  - AxeOSSensor: Generic sensor that reads a single key from API data.
  - AxeOSBootTimeSensor: Calculates device boot time from uptime seconds.
  - AxeOSEnergySensor: Accumulates kWh from power readings over time.
  - AxeOSUptimePercentSensor: Tracks monthly availability percentage.

The Energy and Uptime sensors use RestoreEntity to persist their values
across Home Assistant restarts.
"""

import logging
import time
import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import AxeOSEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id
    entry_name = entry.title

    sensors = [
        # Boot time (diagnostic) — computed from uptimeSeconds
        AxeOSBootTimeSensor(coordinator, entry_id, entry_name),
        # Mining performance
        AxeOSSensor(coordinator, "hashRate", "Current Hashrate", "GH/s", "mdi:pickaxe", None, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "power", "Power", "W", "mdi:flash", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "frequency", "ASIC Frequency", "MHz", "mdi:memory", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        # Temperatures
        AxeOSSensor(coordinator, "temp", "ASIC Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "vrTemp", "VRM Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        # Fan (diagnostic — the main fan entity is in fan.py)
        AxeOSSensor(coordinator, "fanrpm", "Fan RPM", "RPM", "mdi:fan", None, SensorStateClass.MEASUREMENT, entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "fanspeed", "Fan Speed", PERCENTAGE, "mdi:fan", None, SensorStateClass.MEASUREMENT, entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSFanModeSensor(coordinator, entry_id, entry_name),
        # Share counters
        AxeOSSensor(coordinator, "sharesAccepted", "Shares Accepted", "Shares", "mdi:check-circle", None, SensorStateClass.TOTAL_INCREASING, entry_id, entry_name),
        AxeOSSensor(coordinator, "sharesRejected", "Shares Rejected", "Shares", "mdi:close-circle", None, SensorStateClass.TOTAL_INCREASING, entry_id, entry_name),
        # Network (diagnostic)
        AxeOSSensor(coordinator, "wifiRSSI", "WiFi RSSI", "dBm", "mdi:wifi", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        # Best difficulty shares
        AxeOSSensor(coordinator, "bestDiff", "Best Share", None, "mdi:trophy", None, None, entry_id, entry_name),
        AxeOSSensor(coordinator, "bestSessionDiff", "Best Session Share", None, "mdi:trophy-award", None, None, entry_id, entry_name),
        # Calculated sensors
        AxeOSEnergySensor(coordinator, entry_id, entry_name),
        AxeOSUptimePercentSensor(coordinator, entry_id, entry_name),
    ]

    async_add_entities(sensors, True)


class AxeOSSensor(AxeOSEntity, SensorEntity):
    """Generic sensor that maps a single API key to a HA sensor."""

    def __init__(self, coordinator, key, name, unit, icon, device_class, state_class, entry_id, entry_name, entity_category=None):
        """Initialize the sensor.

        Args:
            key: The JSON key to read from the API response (e.g. "hashRate").
            name: Display name suffix (HA prepends the device name).
            unit: Unit of measurement (e.g. "GH/s", "W", "°C").
            device_class: HA SensorDeviceClass for proper formatting.
            state_class: HA SensorStateClass for statistics/history.
            entity_category: Optional EntityCategory.DIAGNOSTIC to hide from main UI.
        """
        super().__init__(coordinator, entry_id, entry_name)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def native_value(self):
        """Return the sensor value from API data, rounding floats to 2 decimals."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        if isinstance(val, float):
            return round(val, 2)
        return val


class AxeOSBootTimeSensor(AxeOSEntity, SensorEntity):
    """Calculates when the device last booted.

    The boot time is computed once from (now - uptimeSeconds) and only
    recalculated when the uptime decreases (= the device rebooted).
    This prevents the timestamp from drifting due to polling jitter.
    """

    _attr_name = "Boot Time"
    _attr_icon = "mdi:clock-start"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_uptimeSeconds"
        self._boot_time = None
        self._last_uptime = None  # Tracks previous uptime to detect reboots

    def _handle_coordinator_update(self) -> None:
        """Recalculate boot time only on first read or after a reboot."""
        if self.coordinator.data:
            uptime = self.coordinator.data.get("uptimeSeconds")
            if uptime is not None:
                # uptime < _last_uptime means the device rebooted
                if self._last_uptime is None or uptime < self._last_uptime:
                    self._boot_time = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(seconds=uptime)
                    )
                self._last_uptime = uptime
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the computed boot time as a UTC datetime."""
        return self._boot_time


class AxeOSEnergySensor(AxeOSEntity, RestoreEntity, SensorEntity):
    """Accumulates energy consumption (kWh) from power readings.

    How it works:
      - On each coordinator update, reads the current power (watts).
      - Multiplies power × elapsed seconds since last update to get
        watt-seconds, then converts to kWh.
      - Uses time.monotonic() so NTP clock adjustments don't cause errors.
      - Skips accumulation when the device is offline.
      - Caps elapsed time to 120s to ignore HA-downtime gaps.
      - Uses RestoreEntity so the total survives HA restarts.
    """

    _attr_name = "Energy"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 5

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_energy"
        self._energy_kwh = 0.0
        self._last_update_time = None  # time.monotonic() of last successful poll

    async def async_added_to_hass(self) -> None:
        """Restore the previous energy total when HA restarts."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._energy_kwh = float(last_state.state)
                _LOGGER.debug("Restored energy value: %s kWh", self._energy_kwh)
            except (ValueError, TypeError):
                self._energy_kwh = 0.0

    def _handle_coordinator_update(self) -> None:
        """Accumulate energy on each successful poll."""
        current_time = time.monotonic()

        if self.coordinator.last_update_success and self.coordinator.data:
            power = self.coordinator.data.get("power")

            if power is not None and self._last_update_time is not None:
                elapsed = current_time - self._last_update_time
                # Only count normal polling intervals (skip gaps > 2 min)
                if 0 < elapsed <= 120:
                    added_kwh = (power * elapsed) / 3_600_000.0
                    self._energy_kwh += added_kwh
                    _LOGGER.debug(
                        "Energy sensor updated. Power: %s W, Elapsed: %s s, Added: %s kWh, Total: %s kWh",
                        power, round(elapsed, 2), round(added_kwh, 7), round(self._energy_kwh, 7)
                    )
                else:
                    _LOGGER.debug("Skipping energy update: elapsed time %s s outside acceptable range", elapsed)

            self._last_update_time = current_time
        elif not self.coordinator.last_update_success:
            # Device offline — reset timer so the offline gap isn't counted
            _LOGGER.debug("Device offline, resetting energy update timer")
            self._last_update_time = None

        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return accumulated energy in kWh."""
        return round(self._energy_kwh, 6)


class AxeOSUptimePercentSensor(AxeOSEntity, RestoreEntity, SensorEntity):
    """Tracks monthly uptime as a percentage (like server SLA).

    How it works:
      - Counts total monitored seconds and total "online" seconds.
      - A poll where last_update_success is True counts as online time.
      - Resets both counters on the 1st of each month.
      - Stores raw counters as extra_state_attributes so RestoreEntity
        can recover them after an HA restart mid-month.
    """

    _attr_name = "Uptime Percentage"
    _attr_icon = "mdi:percent-circle"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_uptime_percent"
        self._total_monitored = 0.0   # Total seconds we've been tracking
        self._total_uptime = 0.0      # Seconds the device was reachable
        self._last_time = None        # time.monotonic() of last check
        now = datetime.datetime.now()
        self._current_year = now.year
        self._current_month = now.month

    async def async_added_to_hass(self) -> None:
        """Restore counters from the last HA session."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                attrs = last_state.attributes or {}
                self._total_monitored = float(attrs.get("total_monitored_seconds", 0))
                self._total_uptime = float(attrs.get("total_uptime_seconds", 0))
            except (ValueError, TypeError):
                pass

    def _handle_coordinator_update(self) -> None:
        """Update uptime counters, resetting on month rollover."""
        current_time = time.monotonic()
        now = datetime.datetime.now()

        # Reset on the 1st of each month (tracks year to handle Dec→Jan)
        if (now.year, now.month) != (self._current_year, self._current_month):
            self._total_monitored = 0.0
            self._total_uptime = 0.0
            self._current_year = now.year
            self._current_month = now.month

        if self._last_time is not None:
            elapsed = current_time - self._last_time
            # Ignore gaps > 1 hour (HA was likely shut down)
            if 0 < elapsed < 3600:
                self._total_monitored += elapsed
                if self.coordinator.last_update_success:
                    self._total_uptime += elapsed

        self._last_time = current_time
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return uptime as a percentage (0.00 – 100.00)."""
        if self._total_monitored == 0:
            return 100.0 if self.coordinator.last_update_success else 0.0
        return round((self._total_uptime / self._total_monitored) * 100.0, 2)

    @property
    def extra_state_attributes(self):
        """Expose raw counters so they survive HA restarts."""
        return {
            "total_monitored_seconds": round(self._total_monitored, 1),
            "total_uptime_seconds": round(self._total_uptime, 1),
        }


class AxeOSFanModeSensor(AxeOSEntity, SensorEntity):
    """Sensor that displays the current fan control mode (Auto/Manual)."""

    _attr_name = "Fan Mode"
    _attr_icon = "mdi:fan-auto"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_fan_mode"

    @property
    def native_value(self):
        """Return 'Auto' or 'Manual' based on autofanspeed."""
        if not self.coordinator.data:
            return None
        return "Auto" if self.coordinator.data.get("autofanspeed") == 1 else "Manual"
