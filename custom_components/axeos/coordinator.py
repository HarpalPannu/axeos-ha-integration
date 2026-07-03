"""Data coordinator for the AxeOS integration.

Handles all communication with the Bitaxe device:
  - Polls GET /api/system/info on a timer for live telemetry data.
  - Sends PATCH /api/system commands (fan speed, toggles, etc.) with
    concurrency protection via an asyncio.Lock.

All entity platforms read from this single coordinator to minimise
network traffic to the device.
"""

import logging
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AxeOSDataCoordinator(DataUpdateCoordinator):
    """Fetches data from the AxeOS API and provides a command interface."""

    def __init__(self, hass, url, api_url, session, update_interval):
        """Initialize the coordinator.

        Args:
            url: The GET endpoint for reading telemetry (/api/system/info).
            api_url: The PATCH endpoint for sending commands (/api/system).
            session: HA-managed aiohttp session.
            update_interval: How often to poll the device.
        """
        self.url = url
        self.api_url = api_url
        self.session = session
        # Lock ensures rapid commands (e.g. two quick fan speed changes)
        # are applied in order, not concurrently
        self._command_lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from the device.

        Raises UpdateFailed on any error so that
        coordinator.last_update_success accurately reflects device state.
        This is important because the energy sensor and uptime sensor
        rely on last_update_success to detect offline periods.
        """
        try:
            async with asyncio.timeout(10):
                async with self.session.get(self.url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_send_command(self, payload):
        """Send a PATCH command to the device.

        Uses an asyncio.Lock so that concurrent calls (e.g. user slides
        the fan speed twice quickly) are serialised. After the command
        succeeds, waits 3 seconds for the device to apply the change,
        then triggers a data refresh so the UI updates immediately.

        Args:
            payload: Dict of key/value pairs to PATCH to the device.
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

            # Device needs a moment to apply the change before we re-read
            await asyncio.sleep(3)
            await self.async_request_refresh()
