"""AxeOS binary sensor platform."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import DOMAIN
from .entity import AxeOSEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [AxeOSConnectivitySensor(coordinator, entry.entry_id, entry.title)], True
    )


class AxeOSConnectivitySensor(AxeOSEntity, BinarySensorEntity):
    """Connectivity sensor for AxeOS."""

    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_online"

    @property
    def is_on(self):
        """Return true if the node is online."""
        return self.coordinator.last_update_success

    @property
    def available(self):
        """Always available so state shows Off when offline, not Unavailable."""
        return True

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"
