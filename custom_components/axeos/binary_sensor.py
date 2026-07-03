"""AxeOS binary sensor platform.

Provides a connectivity sensor that shows whether the Bitaxe device
is reachable. Unlike other entities, this sensor overrides `available`
to always return True so that HA shows "Off" (not "Unavailable") when
the device goes offline.
"""

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
    """Shows whether the Bitaxe device is reachable on the network."""

    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_online"

    @property
    def is_on(self):
        """Return True when the last API poll succeeded."""
        return self.coordinator.last_update_success

    @property
    def available(self):
        """Always return True so the sensor shows Off instead of Unavailable."""
        return True

    @property
    def icon(self):
        """Show a connected or disconnected icon based on state."""
        return "mdi:lan-connect" if self.is_on else "mdi:lan-disconnect"
