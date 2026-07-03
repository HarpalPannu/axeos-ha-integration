"""Base entity for AxeOS integration."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class AxeOSEntity(CoordinatorEntity):
    """Base class for all AxeOS entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        sw_version = "Unknown"
        if isinstance(self.coordinator.data, dict):
            sw_version = self.coordinator.data.get("axeOSVersion", "Unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._entry_name,
            manufacturer="Bitaxe",
            model="AxeOS",
            sw_version=sw_version,
        )
