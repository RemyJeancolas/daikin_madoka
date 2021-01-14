"""Platform for the Daikin AC."""
import asyncio
from datetime import timedelta
import logging

from pymadoka import Controller, discover_devices, force_device_disconnect
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_DEVICES,
    CONF_FORCE_UPDATE,
    CONF_DEVICE,
    CONF_SCAN_INTERVAL,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType


from . import config_flow  # noqa: F401
from .const import CONTROLLERS

LOGGER = logging.getLogger(__name__)

DOMAIN = "daikin_madoka"

PARALLEL_UPDATES = 0
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

COMPONENT_TYPES = ["climate", "sensor"]

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_DEVICES, default=[]): vol.All(
                        cv.ensure_list, [cv.string]
                    ),
                    vol.Optional(CONF_FORCE_UPDATE, default=True): bool,
                    vol.Optional(CONF_DEVICE, default="hci0"): cv.string,
                    vol.Optional(CONF_SCAN_INTERVAL, default=5): cv.positive_int,
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)



async def async_setup(hass, config):
    """Set up the component."""

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=conf,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):

    """Pass conf to all the components."""

    controllers = {}
    for device in entry.data[CONF_DEVICES]:
        if entry.data[CONF_FORCE_UPDATE]:
            await force_device_disconnect(device)
        controllers[device] = Controller(
            device,
            adapter=entry.data[CONF_DEVICE]
        )
       
    await discover_devices(adapter = entry.data[CONF_DEVICE], timeout = entry.data[CONF_SCAN_INTERVAL])

    for device,controller in controllers.items():
        try:
            await controller.start()
        except ConnectionAbortedError as e:
            LOGGER.error(f"Could not connect to device {device}: {str(e)}")


    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CONTROLLERS] = controllers
    for component in COMPONENT_TYPES:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await asyncio.wait(
        [
            hass.config_entries.async_forward_entry_unload(config_entry, component)
            for component in COMPONENT_TYPES
        ]
    )
    #hass.data[DOMAIN].pop(config_entry.entry_id)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    return True
