import logging
import async_timeout

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS numbers based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_name = entry.title

    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    api_url = f"{host.rstrip('/')}/api/system"
    session = async_get_clientsession(hass)

    numbers = [
        AxeOSTargetTempNumber(coordinator, api_url, session, entry.entry_id, entry_name)
    ]

    async_add_entities(numbers, True)


class AxeOSTargetTempNumber(CoordinatorEntity, NumberEntity):
    """Representation of an AxeOS target temperature number."""

    def __init__(self, coordinator, api_url, session, entry_id, entry_name):
        """Initialize the number."""
        super().__init__(coordinator)
        self._api_url = api_url
        self._session = session
        self._entry_id = entry_id
        self._entry_name = entry_name

    @property
    def name(self):
        """Return the formatted name of the number."""
        return f"{self._entry_name} Target Temperature"

    @property
    def unique_id(self):
        """Return a globally unique ID for the number."""
        return f"{self._entry_id}_targetTemp"

    @property
    def icon(self):
        """Return the icon of the number."""
        return "mdi:thermometer-auto"

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def native_min_value(self):
        """Return the minimum value."""
        return 30

    @property
    def native_max_value(self):
        """Return the maximum value."""
        return 90

    @property
    def native_step(self):
        """Return the step value."""
        return 1

    @property
    def native_value(self):
        """Return the current value."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("fanTemp", self.coordinator.data.get("targetTemp", 60))

    async def _send_patch(self, payload):
        """Send a PATCH request to the API."""
        import asyncio
        try:
            async with async_timeout.timeout(10):
                async with self._session.patch(
                    self._api_url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response.raise_for_status()
            
            await asyncio.sleep(2)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to update AxeOS target temperature: %s", err)

    async def async_set_native_value(self, value: float) -> None:
        """Set the new target temperature."""
        # Try both common payload keys to maximize compatibility
        await self._send_patch({"fanTemp": int(value), "targetTemp": int(value)})

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
