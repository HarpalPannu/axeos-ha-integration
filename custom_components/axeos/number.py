"""AxeOS number platform.

Provides a numeric slider for the target ASIC temperature. When the fan
is in Auto mode, the Bitaxe tries to maintain this temperature by
adjusting the fan speed automatically.

The API may use "fanTemp" or "targetTemp" depending on firmware version,
so we send both keys on writes and try both on reads.
"""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .entity import AxeOSEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS numbers based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [AxeOSTargetTempNumber(coordinator, entry.entry_id, entry.title)], True
    )


class AxeOSTargetTempNumber(AxeOSEntity, NumberEntity):
    """Slider to set the target ASIC temperature (30–90 °C)."""

    _attr_name = "Target Temperature"
    _attr_icon = "mdi:thermometer-auto"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 30
    _attr_native_max_value = 90
    _attr_native_step = 1

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the number."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_targetTemp"

    @property
    def native_value(self):
        """Return the current target temp from the API.

        Tries "fanTemp" first, falls back to "targetTemp". Returns None
        (not a hardcoded default) if neither key exists.
        """
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("fanTemp")
        if val is not None:
            return val
        return self.coordinator.data.get("targetTemp")

    async def async_set_native_value(self, value: float) -> None:
        """Send the new target temperature to the device.

        Sends both "fanTemp" and "targetTemp" to cover all firmware versions.
        """
        await self.coordinator.async_send_command(
            {"fanTemp": int(value), "targetTemp": int(value)}
        )
