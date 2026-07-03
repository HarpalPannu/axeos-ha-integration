import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_name = entry.title

    sensors = [
        AxeOSConnectivitySensor(coordinator, entry.entry_id, entry_name)
    ]

    async_add_entities(sensors, True)


class AxeOSConnectivitySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an AxeOS connectivity sensor."""

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def name(self):
        """Return the formatted name of the sensor."""
        return f"{self._entry_name} Online"

    @property
    def unique_id(self):
        """Return a globally unique ID for the sensor."""
        return f"{self._entry_id}_online"

    @property
    def device_class(self):
        """Return the device class."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self):
        """Return true if the node is online."""
        return self.coordinator.last_update_success

    @property
    def available(self):
        """Always return True so the state shows as Off when offline, not Unavailable."""
        return True

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._entry_name,
            manufacturer="Bitaxe",
            model="AxeOS",
            sw_version=self.coordinator.data.get("axeOSVersion", "Unknown") if self.coordinator.data and isinstance(self.coordinator.data, dict) else "Unknown",
        )
