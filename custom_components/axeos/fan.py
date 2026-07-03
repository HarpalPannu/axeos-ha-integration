"""AxeOS fan platform."""

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .const import DOMAIN
from .entity import AxeOSEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS fan based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [AxeOSFan(coordinator, entry.entry_id, entry.title)], True
    )


class AxeOSFan(AxeOSEntity, FanEntity):
    """Representation of an AxeOS fan."""

    _attr_name = "Fan"
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the fan."""
        super().__init__(coordinator, entry_id, entry_name)
        self._attr_unique_id = f"{entry_id}_fan"
        self._attr_preset_modes = ["Auto", "Manual"]

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        if not self.coordinator.data:
            return None
        return "Auto" if self.coordinator.data.get("autofanspeed") == 1 else "Manual"

    @property
    def is_on(self):
        """Return true if the fan is on.

        The fan is considered 'on' when in Auto mode (regardless of
        current RPM) or when in Manual mode with speed > 0.
        """
        if not self.coordinator.data:
            return None
        if self.coordinator.data.get("autofanspeed") == 1:
            return True
        return self.coordinator.data.get("fanspeed", 0) > 0

    @property
    def percentage(self):
        """Return the current speed percentage."""
        if not self.coordinator.data:
            return None
        return int(self.coordinator.data.get("fanspeed", 0))

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            await self.coordinator.async_send_command({"fanspeed": percentage})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == "Auto":
            await self.coordinator.async_send_command({"autofanspeed": 1})
        elif preset_mode == "Manual":
            await self.coordinator.async_send_command({"autofanspeed": 0})

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        """Turn on the fan."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.coordinator.async_send_command({"fanspeed": percentage})
        else:
            await self.coordinator.async_send_command({"fanspeed": 100})

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.coordinator.async_send_command({"fanspeed": 0})
