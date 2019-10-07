import asyncio
import requests
import functools as ft
import json
import logging
import hvac_ir
from typing import Any, Dict, List, Optional

DOMAIN = "hvac_ir"

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    CONF_NAME,
    CONF_HOST,
    CONF_TYPE,
    CONF_DEVICE,
)
from homeassistant.components.climate.const import (
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_OFF,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_MIDDLE,
    SWING_OFF,
    SWING_BOTH,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,

)

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceDataType
from homeassistant.util.temperature import convert as convert_temperature

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | \
                SUPPORT_FAN_MODE | \
                SUPPORT_SWING_MODE

MODES_MAP = {
    HVAC_MODE_COOL: 'cool',
    HVAC_MODE_HEAT: 'heat',
    HVAC_MODE_AUTO: 'auto',
    HVAC_MODE_DRY: 'dry',
    HVAC_MODE_FAN_ONLY: 'fan',
    HVAC_MODE_OFF: 'off',
}

FANS_MAP = {
    FAN_AUTO: 'auto',
    FAN_LOW: 'low',
    FAN_MEDIUM: 'medium',
    FAN_HIGH: 'highest',
}

SWINGS_MAP = {
    SWING_OFF: ['auto', 'auto'],
    SWING_BOTH: ['swing', 'swing'],
    SWING_VERTICAL: ['swing', 'auto'],
    SWING_HORIZONTAL: ['auto', 'swing'],
}

DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TYPE): cv.string,
    vol.Optional(CONF_DEVICE, default="remo"): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([HvacIrRemoClimate(
        config[CONF_NAME], config[CONF_HOST], \
        config[CONF_TYPE], config[CONF_DEVICE])])
    return True

"""
async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    devs = [
        HvacIrRemoClimate(config[CONF_NAME], config[CONF_HOST], \
            config[CONF_TYPE], config[CONF_DEVICE])
    ]
    add_entities(devs, True)
    return True
"""

class HvacIrRemoClimate(ClimateDevice):
    def send_command(self):
        self._sender.send(self._sender.POWER_OFF \
            if self._mode == HVAC_MODE_OFF else self._sender.POWER_ON, \
            MODES_MAP.get(self._mode), \
            FANS_MAP.get(self._fan_mode), \
            self._target_temperature, \
            SWINGS_MAP.get(self._swing_mode)[0], \
            SWINGS_MAP.get(self._swing_mode)[1], \
            False
        )
        self._signal =  self._sender.get_durations()
        jsonstr = json.dumps({
            "format": self._format, "freq": 38, \
            "data": list(map(lambda x: x * self._resolution, self._signal))
        })
        resp = requests.post(
            self._endpoint, jsonstr,
            headers = {
                "X-Requested-With": "curl",
                "Expect": ""
            }
        )
        self._sender.durations = []

    def __init__(self, name, host, type, device = "remo"):
        self._name = name
        self._host = host
        self._type = type.lower()
        self._device = device.lower()
        self._format = "raw" if self._device == "irkit" else "us"
        self._resolution = 2 if self._device == "irkit" else 1
        Sender = hvac_ir.get_sender(self._type)
        self._sender = Sender()
        if self._sender is None:
            _LOGGER.error("Invalid device type: [{}]".format(self._type))
            return
        self._endpoint = "http://{}/messages".format(self._host)
        self._signal = None
        self._support_flags = SUPPORT_FLAGS
        self._modes = [
            HVAC_MODE_COOL,
            HVAC_MODE_HEAT,
            HVAC_MODE_AUTO,
            HVAC_MODE_DRY,
            HVAC_MODE_FAN_ONLY,
            HVAC_MODE_OFF,
        ]
        self._mode = HVAC_MODE_OFF
        self._fan_modes = [
            FAN_AUTO,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
        ]
        self._fan_mode = FAN_AUTO
        self._target_temperature = 23
        self._swing_modes = [
            SWING_OFF,
            SWING_BOTH,
            SWING_VERTICAL,
            SWING_HORIZONTAL,
        ]
        self._swing_mode = SWING_OFF

    @property
    def name(self) -> str:
        return self._name

    @property
    def supported_features(self) -> int:
        return self._support_flags

    @property
    def min_temp(self) -> float:
        return convert_temperature(
            DEFAULT_MIN_TEMP, TEMP_CELSIUS, self.temperature_unit
        )

    @property
    def max_temp(self) -> float:
        return convert_temperature(
            DEFAULT_MAX_TEMP, TEMP_CELSIUS, self.temperature_unit
        )

    @property
    def hvac_mode(self) -> str:
        return self._mode

    @property
    def hvac_modes(self) -> List[str]:
        return self._modes

    @property
    def target_temperature(self) -> Optional[float]:
        return self._target_temperature

    @property
    def target_temperature_step(self) -> float:
        return 1

    @property
    def temperature_unit(self) -> str:
        return TEMP_CELSIUS

    @property
    def fan_mode(self) -> Optional[str]:
        return self._fan_mode

    @property
    def fan_modes(self) -> Optional[List[str]]:
        return self._fan_modes

    @property
    def swing_mode(self) -> Optional[str]:
        return self._swing_mode

    @property
    def swing_modes(self) -> Optional[List[str]]:
        return self._swing_modes

    def set_hvac_mode(self, hvac_mode: str) -> None:
        self._mode = hvac_mode
        self.send_command()

    async def async_set_hvac_mode(self, hvac_mode):
        await self.hass.async_add_executor_job(self.set_hvac_mode, hvac_mode)

    def set_fan_mode(self, fan_mode: str) -> None:
        self._mode = fan_mode
        self.send_command()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.hass.async_add_executor_job(self.set_fan_mode, fan_mode)

    def set_swing_mode(self, swing_mode: str) -> None:
        self._swing_mode = swing_mode
        self.send_command()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self.hass.async_add_executor_job(self.set_swing_mode, swing_mode)

    def set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = int(temperature)
        self.send_command()

    async def async_set_temperature(self, **kwargs) -> None:
        await self.hass.async_add_executor_job(
            ft.partial(self.set_temperature, **kwargs)
        )
