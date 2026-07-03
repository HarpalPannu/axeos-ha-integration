import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_name = entry.title

    sensors = [
        AxeOSSensor(coordinator, "uptimeSeconds", "Uptime", "s", "mdi:clock-start", SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "hashRate", "Current Hashrate", "GH/s", "mdi:pickaxe", None, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "power", "Power", "W", "mdi:flash", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "frequency", "ASIC Frequency", "MHz", "mdi:memory", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "temp", "ASIC Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "vrTemp", "VRM Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "fanrpm", "Fan RPM", "RPM", "mdi:fan", None, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "sharesAccepted", "Shares Accepted", "Shares", "mdi:check-circle", None, SensorStateClass.TOTAL_INCREASING, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "sharesRejected", "Shares Rejected", "Shares", "mdi:close-circle", None, SensorStateClass.TOTAL_INCREASING, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "wifiRSSI", "WiFi RSSI", "dBm", "mdi:wifi", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
    ]

    async_add_entities(sensors, True)


class AxeOSSensor(CoordinatorEntity, SensorEntity):
    """Native implementation of an AxeOS sensor using CoordinatorEntity."""

    def __init__(self, coordinator, key, name, unit, icon, device_class, state_class, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._unit = unit
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def name(self):
        """Return the formatted name of the sensor."""
        return f"{self._entry_name} {self._name}"

    @property
    def unique_id(self):
        """Return a globally unique ID for the sensor."""
        return f"{self._entry_id}_{self._key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        if isinstance(val, float):
            return round(val, 2)
        return val

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the state class."""
        return self._state_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._entry_name,
            manufacturer="Bitaxe",
            model="AxeOS",
            sw_version=self.coordinator.data.get("axeOSVersion", "Unknown") if self.coordinator.data else "Unknown",
        )
