"""AxeOS sensor platform."""

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
        AxeOSBootTimeSensor(coordinator, entry_id, entry_name),
        AxeOSSensor(coordinator, "hashRate", "Current Hashrate", "GH/s", "mdi:pickaxe", None, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "power", "Power", "W", "mdi:flash", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "frequency", "ASIC Frequency", "MHz", "mdi:memory", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "temp", "ASIC Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "vrTemp", "VRM Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry_id, entry_name),
        AxeOSSensor(coordinator, "fanrpm", "Fan RPM", "RPM", "mdi:fan", None, SensorStateClass.MEASUREMENT, entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "sharesAccepted", "Shares Accepted", "Shares", "mdi:check-circle", None, SensorStateClass.TOTAL_INCREASING, entry_id, entry_name),
        AxeOSSensor(coordinator, "sharesRejected", "Shares Rejected", "Shares", "mdi:close-circle", None, SensorStateClass.TOTAL_INCREASING, entry_id, entry_name),
        AxeOSSensor(coordinator, "wifiRSSI", "WiFi RSSI", "dBm", "mdi:wifi", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "bestDiff", "Best Share", None, "mdi:trophy", None, None, entry_id, entry_name),
        AxeOSSensor(coordinator, "bestSessionDiff", "Best Session Share", None, "mdi:trophy-award", None, None, entry_id, entry_name),
        AxeOSEnergySensor(coordinator, entry_id, entry_name),
        AxeOSUptimePercentSensor(coordinator, entry_id, entry_name),
    ]

    async_add_entities(sensors, True)


class AxeOSSensor(AxeOSEntity, SensorEntity):
    """Generic AxeOS sensor that reads a key from coordinator data."""

    def __init__(self, coordinator, key, name, unit, icon, device_class, state_class, entry_id, entry_name, entity_category=None):
        """Initialize the sensor."""
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
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        if isinstance(val, float):
            return round(val, 2)
        return val


class AxeOSBootTimeSensor(AxeOSEntity, SensorEntity):
    """Boot time sensor — calculates when the device last started.

    The boot time is computed once on first update and only recalculated
    when the uptime value decreases (indicating a device reboot), which
    eliminates the timestamp drift caused by repeated recalculation.
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
        self._last_uptime = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            uptime = self.coordinator.data.get("uptimeSeconds")
            if uptime is not None:
                # Only (re)calculate boot time on first reading or after reboot
                if self._last_uptime is None or uptime < self._last_uptime:
                    self._boot_time = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(seconds=uptime)
                    )
                self._last_uptime = uptime
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the computed boot time."""
        return self._boot_time


class AxeOSEnergySensor(AxeOSEntity, RestoreEntity, SensorEntity):
    """Energy sensor that accumulates kWh from power readings.

    Uses time.monotonic() for elapsed-time calculations (immune to NTP
    clock adjustments), RestoreEntity to survive HA restarts without
    resetting to zero, and real timestamps instead of dict-equality
    checks so no polling interval is ever silently skipped.
    """

    _attr_name = "Energy"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_energy"
        self._energy_kwh = 0.0
        self._last_update_time = None

    async def async_added_to_hass(self) -> None:
        """Restore previous energy total on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._energy_kwh = float(last_state.state)
            except (ValueError, TypeError):
                self._energy_kwh = 0.0

    def _handle_coordinator_update(self) -> None:
        """Accumulate energy on each successful data fetch."""
        current_time = time.monotonic()

        if self.coordinator.last_update_success and self.coordinator.data:
            power = self.coordinator.data.get("power")

            if power is not None and self._last_update_time is not None:
                elapsed = current_time - self._last_update_time
                # Only accumulate for normal polling gaps (≤ 2 min)
                if 0 < elapsed <= 120:
                    self._energy_kwh += (power * elapsed) / 3_600_000.0

            self._last_update_time = current_time
        elif not self.coordinator.last_update_success:
            # Device offline — reset timer so the offline gap is never counted
            self._last_update_time = None

        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the accumulated energy in kWh."""
        return round(self._energy_kwh, 6)


class AxeOSUptimePercentSensor(AxeOSEntity, RestoreEntity, SensorEntity):
    """Monthly uptime percentage sensor.

    Tracks the ratio of successful polls to total monitored time within
    the current calendar month. Resets automatically on month rollover
    and persists its counters across HA restarts via RestoreEntity.
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
        self._total_monitored = 0.0
        self._total_uptime = 0.0
        self._last_time = None
        now = datetime.datetime.now()
        self._current_year = now.year
        self._current_month = now.month

    async def async_added_to_hass(self) -> None:
        """Restore previous counters on HA restart."""
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
        """Update uptime tracking counters."""
        current_time = time.monotonic()
        now = datetime.datetime.now()

        # Reset counters on month rollover (tracks year too)
        if (now.year, now.month) != (self._current_year, self._current_month):
            self._total_monitored = 0.0
            self._total_uptime = 0.0
            self._current_year = now.year
            self._current_month = now.month

        if self._last_time is not None:
            elapsed = current_time - self._last_time
            # Cap to 1 hour to ignore HA-offline gaps
            if 0 < elapsed < 3600:
                self._total_monitored += elapsed
                if self.coordinator.last_update_success:
                    self._total_uptime += elapsed

        self._last_time = current_time
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the uptime percentage for the current month."""
        if self._total_monitored == 0:
            return 100.0 if self.coordinator.last_update_success else 0.0
        return round((self._total_uptime / self._total_monitored) * 100.0, 2)

    @property
    def extra_state_attributes(self):
        """Expose raw counters so they survive HA restarts via RestoreEntity."""
        return {
            "total_monitored_seconds": round(self._total_monitored, 1),
            "total_uptime_seconds": round(self._total_uptime, 1),
        }
