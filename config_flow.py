"""Config flow for the Daikin platform."""

import logging
import re
import asyncio
import voluptuous as vol

from pymadoka import Controller, discover_devices, force_device_disconnect

from homeassistant import config_entries
from homeassistant.const import (
    CONF_DEVICES,
    CONF_DEVICE, CONF_DISCOVERY,
    CONF_SCAN_INTERVAL,
    CONF_FORCE_UPDATE,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)



@config_entries.HANDLERS.register("daikin_madoka")
class FlowHandler(config_entries.ConfigFlow, domain="daikin_madoka"):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Daikin config flow."""

    @property
    def schema(self):
        """Return current schema."""

        return vol.Schema(
            {
                vol.Required(CONF_DEVICES, default=[]): cv.string,
                vol.Optional(CONF_DISCOVERY, default=True): bool,
                vol.Optional(CONF_FORCE_UPDATE, default=True): bool,
                vol.Optional(CONF_DEVICE, default="hci0"): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=5): cv.positive_int,
            }
        )

    
    async def _create_entry(
        self, devices, scan_interval=None, force_update=None, device=None
    ):
        """Register new entry."""
        if not self.unique_id:
            await self.async_set_unique_id("BRC1H-id")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="BRC1H",
            data={
                CONF_DEVICES: list(map(lambda x: x.strip(), devices.split(","))),
                CONF_DEVICE: device,
                CONF_SCAN_INTERVAL: scan_interval,
                CONF_FORCE_UPDATE: force_update,
                CONF_DISCOVERY: False
            },
        )

    def validate_macs(self,macs):
        for mac in macs: 
            if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower()):
                return False
        return True


                
    async def is_valid_adapter(self,adapter):

        """Check the adapter configuration using hcitool.
        """
        try:
            await discover_devices(timeout = 1, 
                                  adapter = adapter)
            return True
        except Exception as e:
            return False 


    async def async_step_user(self, user_input=None):
        """User initiated config flow."""
        errors = {}
        macs = []
        if user_input is not None:
           
           # Check if all the devices are valid MAC addresses
            macs = list(map(lambda x: x.strip(),  user_input[CONF_DEVICES].split(",")))
            if not self.validate_macs(macs):
                errors[CONF_DEVICES] = "not_a_mac"
            
            # Check if the adapter exists
            is_valid_adapter = await self.is_valid_adapter(user_input[CONF_DEVICE])
            if not is_valid_adapter:
                errors[CONF_DEVICE] = "cannot_connect"

            # Input is valid, set data.
            if not errors:

                if user_input[CONF_DISCOVERY]:

                    # Disconnect all the devices so they can be found

                    for d in macs:
                        await force_device_disconnect(d)

                    # Discover devices
                    devices = await discover_devices()
                    devices = set(devices)
                    discovered_macs = set(list(map(lambda x:x.address,devices)))
                    not_found = set(macs) - discovered_macs

                    # Check if all the devices have been found
                    if len(not_found)>0:
                        errors[CONF_DEVICES] = "device_not_found"

                if not errors:
                    return await self._create_entry(user_input[CONF_DEVICES],
                                                user_input.get(CONF_SCAN_INTERVAL),
                                                user_input.get(CONF_FORCE_UPDATE),
                                                user_input.get(CONF_DEVICE),
                                                 )
        if user_input is None or len(errors)>0:
             return self.async_show_form(step_id="user", data_schema=self.schema, errors = errors)
       

    async def async_step_import(self, user_input):
        """Import a config entry."""
        devices = user_input.get(CONF_DEVICES)
        if not devices:
            return await self.async_step_user()
        return await self._create_entry(
            user_input[CONF_DEVICES],
            user_input.get(CONF_SCAN_INTERVAL),
            user_input.get(CONF_FORCE_UPDATE),
            user_input.get(CONF_DEVICE),
        )
