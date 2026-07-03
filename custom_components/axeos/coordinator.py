import logging
import async_timeout

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class AxeOSDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API securely and efficiently."""

    def __init__(self, hass, url, session, update_interval):
        """Initialize the data updater."""
        self.url = url
        self.session = session
        self._failed_attempts = 0

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with async_timeout.timeout(10):
                async with self.session.get(self.url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Reset failure count on success
                    if self._failed_attempts > 0:
                        _LOGGER.info("Connection to AxeOS restored.")
                        self._failed_attempts = 0
                        
                    return data
        except Exception as err:
            self._failed_attempts += 1
            if self._failed_attempts <= 5:
                # Return last known data to tolerate transient drops
                _LOGGER.debug("Transient API drop (%s/5): %s", self._failed_attempts, err)
                if self.data:
                    return self.data
            
            # After 5 failures, actually raise the error which marks entities as Unavailable
            raise UpdateFailed(f"Error communicating with API: {err}")
