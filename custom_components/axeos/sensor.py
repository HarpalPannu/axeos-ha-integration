import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up AxeOS sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entry_name = entry.title

    sensors = [
        AxeOSSensor(coordinator, "uptimeSeconds", "Boot Time", None, "mdi:clock-start", SensorDeviceClass.TIMESTAMP, None, entry.entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "hashRate", "Current Hashrate", "GH/s", "mdi:pickaxe", None, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "power", "Power", "W", "mdi:flash", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "frequency", "ASIC Frequency", "MHz", "mdi:memory", SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "temp", "ASIC Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "vrTemp", "VRM Temperature", "°C", "mdi:thermometer", SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "fanrpm", "Fan RPM", "RPM", "mdi:fan", None, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "sharesAccepted", "Shares Accepted", "Shares", "mdi:check-circle", None, SensorStateClass.TOTAL_INCREASING, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "sharesRejected", "Shares Rejected", "Shares", "mdi:close-circle", None, SensorStateClass.TOTAL_INCREASING, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "wifiRSSI", "WiFi RSSI", "dBm", "mdi:wifi", SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, entry.entry_id, entry_name, EntityCategory.DIAGNOSTIC),
        AxeOSSensor(coordinator, "bestDiff", "Best Share", None, "mdi:trophy", None, None, entry.entry_id, entry_name),
        AxeOSSensor(coordinator, "bestSessionDiff", "Best Session Share", None, "mdi:trophy-award", None, None, entry.entry_id, entry_name),
        AxeOSEnergySensor(coordinator, entry.entry_id, entry_name),
        AxeOSUptimePercentSensor(coordinator, entry.entry_id, entry_name),
    ]

    async_add_entities(sensors, True)


class AxeOSSensor(CoordinatorEntity, SensorEntity):
    """Native implementation of an AxeOS sensor using CoordinatorEntity."""

    def __init__(self, coordinator, key, name, unit, icon, device_class, state_class, entry_id, entry_name, entity_category=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._unit = unit
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._entry_id = entry_id
        self._entry_name = entry_name
        self._entity_category = entity_category

    @property
    def entity_category(self):
        """Return the category of the entity."""
        return self._entity_category

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data and self._device_class == SensorDeviceClass.TIMESTAMP and self._key == "uptimeSeconds":
            import datetime
            uptime = self.coordinator.data.get(self._key)
            if uptime is not None:
                boot_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=uptime)
                if not hasattr(self, '_boot_time') or not hasattr(self, '_last_uptime') or uptime < getattr(self, '_last_uptime', 0):
                    self._boot_time = boot_time
                elif abs((getattr(self, '_boot_time', boot_time) - boot_time).total_seconds()) > 60:
                    self._boot_time = boot_time
                self._last_uptime = uptime
        super()._handle_coordinator_update()

    @property
    def name(self):
        """Return the formatted name of the sensor."""
        return f"{self._entry_name} {self._name}"

    @property
    def unique_id(self):
        """Return a globally unique ID for the sensor."""
        return f"{self._entry_id}_{self._key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        if self._device_class == SensorDeviceClass.TIMESTAMP and self._key == "uptimeSeconds":
            return getattr(self, '_boot_time', None)

        val = self.coordinator.data.get(self._key)
        if isinstance(val, float):
            return round(val, 2)
        return val

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the state class."""
        return self._state_class

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


class AxeOSEnergySensor(CoordinatorEntity, SensorEntity):
    """Native implementation of an AxeOS Energy sensor."""

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_name = entry_name
        self._energy_kwh = 0.0
        self._last_update_time = None
        self._last_processed_data = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        import time
        current_time = time.time()
        
        if self.coordinator.last_update_success and self.coordinator.data and self.coordinator.data != self._last_processed_data:
            power = self.coordinator.data.get("power")
            
            if power is not None and self._last_update_time is not None:
                elapsed = current_time - self._last_update_time
                # Only calculate if the gap is a normal polling interval (e.g. <= 2 minutes)
                if 0 < elapsed <= 120:
                    added_kwh = (power * elapsed) / 3600000.0
                    self._energy_kwh += added_kwh
                    
            self._last_update_time = current_time
            self._last_processed_data = self.coordinator.data
        elif not self.coordinator.last_update_success:
            # Device is offline. Reset the timer so we don't calculate energy for the offline gap.
            self._last_update_time = None
            
        super()._handle_coordinator_update()

    @property
    def name(self):
        """Return the formatted name of the sensor."""
        return f"{self._entry_name} Energy"

    @property
    def unique_id(self):
        """Return a globally unique ID for the sensor."""
        return f"{self._entry_id}_energy"

    @property
    def state(self):
        """Return the state of the sensor."""
        return round(self._energy_kwh, 6)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "kWh"

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:lightning-bolt"

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        """Return the state class."""
        return SensorStateClass.TOTAL_INCREASING

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


class AxeOSUptimePercentSensor(CoordinatorEntity, SensorEntity):
    """Native implementation of an AxeOS Uptime Percentage sensor."""

    def __init__(self, coordinator, entry_id, entry_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entry_name = entry_name
        self._total_monitored_time = 0.0
        self._total_uptime = 0.0
        self._last_time = None
        
        import datetime
        self._current_month = datetime.datetime.now().month

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        import time
        import datetime
        
        current_time = time.time()
        current_month = datetime.datetime.now().month
        
        # Reset tracker if a new month has started
        if current_month != getattr(self, '_current_month', current_month):
            self._total_monitored_time = 0.0
            self._total_uptime = 0.0
            self._current_month = current_month
        
        if self._last_time is not None:
            elapsed = current_time - self._last_time
            # Cap elapsed to 1 hour to prevent huge jumps if HA was offline
            if 0 < elapsed < 3600:
                self._total_monitored_time += elapsed
                if self.coordinator.last_update_success:
                    self._total_uptime += elapsed
                    
        self._last_time = current_time
        super()._handle_coordinator_update()

    @property
    def name(self):
        """Return the formatted name of the sensor."""
        return f"{self._entry_name} Uptime Percentage"

    @property
    def unique_id(self):
        """Return a globally unique ID for the sensor."""
        return f"{self._entry_id}_uptime_percent"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._total_monitored_time == 0:
            return 100.0 if self.coordinator.last_update_success else 0.0
        pct = (self._total_uptime / self._total_monitored_time) * 100.0
        return round(pct, 2)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return PERCENTAGE

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:percent-circle"

    @property
    def entity_category(self):
        """Return the category of the entity."""
        from homeassistant.helpers.entity import EntityCategory
        return EntityCategory.DIAGNOSTIC

    @property
    def state_class(self):
        """Return the state class."""
        from homeassistant.components.sensor import SensorStateClass
        return SensorStateClass.MEASUREMENT

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
