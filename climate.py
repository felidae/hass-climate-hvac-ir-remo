"""
Demo platform that offers a fake climate device.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/demo/
"""
import asyncio
import logging
import requests
import json
#import socket
from importlib import import_module

#import binascii
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
#from homeassistant.helpers.restore_state import async_get_last_state
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_FAN_MODE, SUPPORT_OPERATION_MODE, SUPPORT_SWING_MODE,
    STATE_AUTO, STATE_COOL, STATE_DRY, STATE_FAN_ONLY, STATE_HEAT)

from homeassistant.const import (ATTR_TEMPERATURE, CONF_TIMEOUT, CONF_HOST, CONF_MAC, CONF_TYPE,
    ATTR_UNIT_OF_MEASUREMENT, CONF_NAME, STATE_OFF)

import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['hvac_ir']

DOMAIN = 'hvac_ir'

DEFAULT_TIMEOUT = 10
DEFAULT_RETRY = 3

DEFAULT_NAME = 'Nature Remo HVAC'
#CONF_SENSOR = otarget_sensor'

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | 
    SUPPORT_OPERATION_MODE | SUPPORT_FAN_MODE)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
  vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
  vol.Required(CONF_HOST): cv.string,
  vol.Required(CONF_TYPE): cv.string,
  vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
  })

# noinspection PyUnusedLocal
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
  actype = config.get(CONF_TYPE)
  import hvac_ir
  cls = hvac_ir.get_sender(actype.lower())
  if cls is None:
    _LOGGER.error("Invalid device type: [{}]".format(actype.lower))
    return
  host = config.get(CONF_HOST)
  #mac = binascii.unhexlify(config.get(CONF_MAC).encode().replace(b':', b''))
  timeout = config.get(CONF_TIMEOUT)
  name = config.get(CONF_NAME)
  #sensor = config.get(CONF_SENSOR)

  _LOGGER.debug("agajglajlkgal")
  async_add_devices([
    NatureRemoClimate(hass, name, host, timeout, cls)
  ])


# noinspection PyAbstractClass
class NatureRemoClimate(ClimateDevice):
  TICK = 32.6
  IR_TOKEN = 0x26

  def __init__(self, hass, name, host, timeout, protocol):
    """Initialize the climate device."""
    self.hass = hass
    self._name = name
    self._host = host
    #self._mac = mac
    self._timeout = timeout
    #self._sensor = sensor
    self._protocol = protocol()
    self._unit = hass.config.units.temperature_unit
    self._target_temperature = 23
    self._current_temperature = None
    self._current_swing_mode = 'auto'
    self._current_fan_mode = 'auto'
    self._current_operation = 'off'
    #self._broadlink_device = broadlink_device

    #self._operations_list = self._protocol.list_modes()
    self._operations_list = list([
      STATE_FAN_ONLY,
      STATE_DRY,
      STATE_COOL,
      STATE_HEAT,
      STATE_AUTO,
    ])
    self._operations_list.insert(0, 'off')
    #self._fan_list = self._protocol.list_fan_speeds()
    self._fan_list = list({
      'auto',
      'low',
      'medium',
      'high',
      'higher',
      'higiest',
    })
    self._swing_list = self._protocol.list_swing_modes()

    """
    if sensor:
      async_track_state_change(
        hass, sensor, self._async_temp_sensor_changed)
      sensor_state = hass.states.get(sensor)
      if sensor_state:
        self._async_update_current_temp(sensor_state)
    """

  @asyncio.coroutine
  def _async_temp_sensor_changed(self, entity_id, old_state, new_state):
    """Handle temperature changes."""
    if new_state is None:
      return

    self._async_update_current_temp(new_state)
    yield from self.async_update_ha_state()

  @callback
  def _async_update_current_temp(self, state):
    """Update thermostat with latest state from sensor."""
    _LOGGER.warning("Update current temp to {}".format(state.state))
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

    try:
      _state = state.state
      if self.represents_float(_state):
        self._current_temperature = self.hass.config.units.temperature(
          float(_state), unit)
    except ValueError as ex:
      _LOGGER.error('Unable to update from sensor: %s', ex)

  @staticmethod
  def represents_float(s):
    try:
      float(s)
      return True
    except ValueError:
      return False

  """
  @classmethod
  def bl_convert(cls, durations):
    result = bytearray()
    result.append(cls.IR_TOKEN)
    result.append(0)  # repeat
    result.append(len(durations) % 256)
    result.append(int(len(durations) / 256))
    for dur in durations:
      num = int(round(dur / cls.TICK))
      if num > 255:
        result.append(0)
        result.append(int(num / 256))
      result.append(num % 256)
    result.append(0x0d)
    result.append(0x05)
    result.append(0x00)
    result.append(0x00)
    result.append(0x00)
    result.append(0x00)
    return result
  """

  def send_command(self):
    op = self._current_operation.lower()
    power = 'on'
    if op == 'off' or op == 'idle':
      power = 'off'
    self._protocol.send(power, op, self._current_fan_mode, int(self._target_temperature), self._current_swing_mode,
      self._protocol.HDIR_AUTO, False)

    _LOGGER.warning("Sending power: {}, op: {}, fan: {}, temp: {}, swing: {}"
      .format(power, op, self._current_fan_mode, self._target_temperature, self._current_swing_mode))
    payload = self._protocol.get_durations()
    resp = requests.post(
      "http://{}/messages".format(self._host),
      json.dumps({"format": "us", "freq": 38, "data": payload}),
      headers = {
        "X-Requested-With": "curl",
        "Expect": ""
      }
    )
    self._protocol.durations = []
    """
    for retry in range(DEFAULT_RETRY):
      try:
        break
      except (socket.timeout, ValueError):
        try:
          #self._broadlink_device.auth()
          pass
        except socket.timeout:
          if retry == DEFAULT_RETRY - 1:
            _LOGGER.error("Failed to send packet to Broadlink RM Device")
    """

  @property
  def supported_features(self):
    """Return the list of supported features."""
    return SUPPORT_FLAGS

  @property
  def should_poll(self):
    """Return the polling state."""
    return False

  @property
  def name(self):
    """Return the name of the climate device."""
    return self._name

  @property
  def temperature_unit(self):
    """Return the unit of measurement."""
    return self._unit

  @property
  def current_temperature(self):
    """Return the current temperature."""
    return self._current_temperature

  @property
  def target_temperature(self):
    """Return the temperature we try to reach."""
    return self._target_temperature

  @property
  def target_temperature_step(self):
    """Return the supported step of target temperature."""
    return 1

  @property
  def current_operation(self):
    """Return current operation ie. heat, cool, idle."""
    return self._current_operation

  @property
  def operation_list(self):
    """Return the list of available operation modes."""
    return self._operations_list

  @property
  def current_fan_mode(self):
    """Return the fan setting."""
    return self._current_fan_mode

  @property
  def fan_list(self):
    """Return the list of available fan modes."""
    return self._fan_list

  def set_temperature(self, **kwargs):
    """Set new target temperatures."""
    if kwargs.get(ATTR_TEMPERATURE) is not None:
      self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
    if not (self._current_operation.lower() == 'off' or self._current_operation.lower() == 'idle'):
      self.send_command()
    self.schedule_update_ha_state()

  def set_swing_mode(self, swing_mode):
    """Set new target temperature."""
    self._current_swing_mode = swing_mode
    if not (self._current_operation.lower() == 'off' or self._current_operation.lower() == 'idle'):
      self.send_command()
    self.schedule_update_ha_state()

  def set_fan_mode(self, fan):
    """Set new target temperature."""
    self._current_fan_mode = fan
    if not (self._current_operation.lower() == 'off' or self._current_operation.lower() == 'idle'):
      self.send_command()
    self.schedule_update_ha_state()

  def set_operation_mode(self, operation_mode):
    """Set new target temperature."""
    self._current_operation = operation_mode
    self.send_command()
    self.schedule_update_ha_state()

  @property
  def current_swing_mode(self):
    """Return the swing setting."""
    return self._current_swing_mode

  @property
  def swing_list(self):
    """List of available swing modes."""
    return self._swing_list

  @asyncio.coroutine
  def async_added_to_hass(self):
    _LOGGER.warning("HVAC-IR/Remo climate added to hass")
    state = yield from RestoreEntity.async_get_last_state(self)

    if state is not None:
      try:
        self._target_temperature = state.attributes['temperature']
        self._current_operation = state.attributes['operation_mode']
        self._current_fan_mode = state.attributes['fan_mode']
        self._current_swing_mode = state.attributes['swing_mode']
      except KeyError:
        pass
