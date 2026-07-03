import logging
import async_timeout

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS switches based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_name = entry.title

    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    api_url = f"{host.rstrip('/')}/api/system"
    session = async_get_clientsession(hass)

    switches = [
        AxeOSAutoFanSwitch(coordinator, api_url, session, entry.entry_id, entry_name)
    ]

    async_add_entities(switches, True)


class AxeOSAutoFanSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an AxeOS auto fan switch."""

    def __init__(self, coordinator, api_url, session, entry_id, entry_name):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._session = session
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def name(self):
        """Return the formatted name of the switch."""
        return f"{self._entry_name} Auto Fan"

    @property
    def unique_id(self):
        """Return a globally unique ID for the switch."""
        return f"{self._entry_id}_autofanspeed"

    @property
    def icon(self):
        """Return the icon of the switch."""
        return "mdi:fan-auto"

    @property
    def is_on(self):
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("autofanspeed") == 1

    async def _send_patch(self, payload):
        """Send a PATCH request to the API."""
        try:
            async with async_timeout.timeout(10):
                async with self._session.patch(
                    self._api_url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
                    await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to update AxeOS auto fan speed: %s", err)

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._send_patch({"autofanspeed": 1})

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._send_patch({"autofanspeed": 0})

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
