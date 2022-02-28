import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from hatch_rest_api import get_rest_minis
import asyncio
from awscrt.mqtt import Connection

from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_MQTT_CONNECTION,
    DATA_REST_MINIS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config_entry: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug(f"async setup")
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"async setup entry: {config_entry}")
    email = config_entry.data[CONF_EMAIL]
    password = config_entry.data[CONF_PASSWORD]

    client_session = async_get_clientsession(hass)
    _, mqtt_connection, rest_minis = await get_rest_minis(email=email, password=password, client_session=client_session)

    data = {
        DATA_MQTT_CONNECTION: mqtt_connection,
        DATA_REST_MINIS: rest_minis,
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    hass.data[DOMAIN] = data

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(f"unload entry")
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        mqtt_connection: Connection = config_entry.data[DATA_MQTT_CONNECTION]
        mqtt_connection.disconnect().result()

        hass.data[DOMAIN] = None

    return unload_ok
