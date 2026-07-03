"""Shared base entity for the AxeOS integration.

Every AxeOS entity (sensor, fan, switch, number, binary_sensor) inherits
from AxeOSEntity. This provides:
  - Consistent device_info so all entities group under one device in HA.
  - has_entity_name = True so HA auto-prefixes the device name to
    entity names (e.g. "Bitaxe" + "Fan" = "Bitaxe Fan").
"""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class AxeOSEntity(CoordinatorEntity):
    """Base class for all AxeOS entities."""

    # Tells HA that entity names are suffixes; the device name is the prefix
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the base entity.

        Args:
            coordinator: The shared AxeOSDataCoordinator instance.
            entry_id: The config entry ID (used for unique_id generation).
            entry_name: The user-chosen friendly name (used as device name).
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def device_info(self) -> DeviceInfo:
        """Link this entity to its device in the HA device registry."""
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
