"""AxeOS Home Assistant Integration.

Sets up the integration from a config entry, creates the shared data
coordinator, and forwards setup to each entity platform (sensor, fan,
number, binary_sensor).
"""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import AxeOSDataCoordinator

_LOGGER = logging.getLogger(__name__)

# All entity platforms this integration provides
PLATFORMS = ["sensor", "fan", "binary_sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AxeOS from a config entry.

    Creates an AxeOSDataCoordinator that polls the device, stores it
    in hass.data, then forwards setup to each platform.
    """
    hass.data.setdefault(DOMAIN, {})

    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    info_url = f"{host.rstrip('/')}/api/system/info"  # GET endpoint (read-only)
    api_url = f"{host.rstrip('/')}/api/system"        # PATCH endpoint (commands)

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 30)
    )

    session = async_get_clientsession(hass)
    coordinator = AxeOSDataCoordinator(
        hass, info_url, api_url, session, timedelta(seconds=scan_interval)
    )

    # Perform the first data fetch; raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the integration whenever the user changes options
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and clean up."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options are changed (host, scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
