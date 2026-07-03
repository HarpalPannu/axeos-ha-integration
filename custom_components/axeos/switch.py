"""AxeOS switch platform.

Provides toggle switches for device features that accept boolean
values via the PATCH /api/system endpoint:
  - Screen Sleep: Turns the physical OLED display on/off.
  - Turn Off LED: Turns the onboard LED on/off.
"""

import logging

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import AxeOSEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS switches based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_id = entry.entry_id
    entry_name = entry.title

    switches = [
        AxeOSSwitch(coordinator, entry_id, entry_name, "screenSleep", "Screen Sleep", "mdi:monitor-off"),
        AxeOSSwitch(coordinator, entry_id, entry_name, "ledOff", "Turn Off LED", "mdi:led-off"),
    ]

    async_add_entities(switches, True)


class AxeOSSwitch(AxeOSEntity, SwitchEntity):
    """Generic boolean switch that maps a single API key to a HA switch.

    Reads the current state from the coordinator data and sends True/False
    via the coordinator's async_send_command() on toggle.
    """

    def __init__(self, coordinator, entry_id, entry_name, key, name, icon):
        """Initialize the switch.

        Args:
            key: The API JSON key this switch controls (e.g. "screenSleep").
            name: Display name suffix.
            icon: MDI icon string.
        """
        super().__init__(coordinator, entry_id, entry_name)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def is_on(self):
        """Return True if the switch is on. Handles both bool and int API values."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        if isinstance(val, bool):
            return val
        return val == 1

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.async_send_command({self._key: True})

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.async_send_command({self._key: False})
