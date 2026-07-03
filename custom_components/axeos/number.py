"""AxeOS number platform."""

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
    """Target temperature number control."""

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
        """Return the current target temperature.

        Returns None instead of a hardcoded fallback when the API
        does not provide a value, so the UI shows 'Unknown' rather
        than a potentially misleading default.
        """
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get("fanTemp")
        if val is not None:
            return val
        return self.coordinator.data.get("targetTemp")

    async def async_set_native_value(self, value: float) -> None:
        """Set the new target temperature."""
        await self.coordinator.async_send_command(
            {"fanTemp": int(value), "targetTemp": int(value)}
        )
