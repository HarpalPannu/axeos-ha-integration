"""Data coordinator for AxeOS integration."""

import logging
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AxeOSDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the AxeOS API."""

    def __init__(self, hass, url, api_url, session, update_interval):
        """Initialize the data updater."""
        self.url = url          # GET  /api/system/info
        self.api_url = api_url  # PATCH /api/system
        self.session = session
        self._command_lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        Raises UpdateFailed immediately on any error so that
        coordinator.last_update_success accurately reflects device state.
        """
        try:
            async with asyncio.timeout(10):
                async with self.session.get(self.url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_send_command(self, payload):
        """Send a PATCH command to the AxeOS API.

        Uses an asyncio.Lock to serialise concurrent commands so rapid
        user actions (e.g. sliding the fan speed twice) are applied in
        order and the subsequent data refresh always reads the final state.
        """
        async with self._command_lock:
            try:
                async with asyncio.timeout(10):
                    async with self.session.patch(
                        self.api_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()
            except Exception as err:
                _LOGGER.error("Failed to send command to AxeOS: %s", err)
                raise

            # Give the device time to apply the change, then refresh
            await asyncio.sleep(3)
            await self.async_request_refresh()
