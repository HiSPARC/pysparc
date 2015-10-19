import logging
import ConfigParser
import weakref
from ast import literal_eval

from atom.api import Atom, observe, Range, Value, Bool, Float, Str

from pysparc.util import map_setting
from pysparc.messages import SetControlParameter, InitializeMessage


logger = logging.getLogger(__name__)


class Config(Atom):

    ch1_voltage = Range(300, 1500, 300)
    ch2_voltage = Range(300, 1500, 300)
    # thresholds are in absolute ADC counts
    ch1_threshold_low = Range(0, 0xfff, 250)
    ch2_threshold_low = Range(0, 0xfff, 250)
    ch1_threshold_high = Range(0, 0xfff, 320)
    ch2_threshold_high = Range(0, 0xfff, 320)

    ch1_integrator_time = Range(0x00, 0xff, 0xff)
    ch2_integrator_time = Range(0x00, 0xff, 0xff)

    ch1_offset_positive = Range(0x00, 0xff, 0x80)
    ch1_offset_negative = Range(0x00, 0xff, 0x80)
    ch2_offset_positive = Range(0x00, 0xff, 0x80)
    ch2_offset_negative = Range(0x00, 0xff, 0x80)
    ch1_gain_positive = Range(0x00, 0xff, 0x80)
    ch1_gain_negative = Range(0x00, 0xff, 0x80)
    ch2_gain_positive = Range(0x00, 0xff, 0x80)
    ch2_gain_negative = Range(0x00, 0xff, 0x80)
    common_offset = Range(0x00, 0xff, 0x00)
    full_scale = Range(0x00, 0xff, 0x00)

    trigger_condition = Range(0x01, 0xff, 0x08)
    one_second_enabled = Bool(False)

    pre_coincidence_time = Range(0, 2000, 1000)
    coincidence_time = Range(0, 5000, 2000)
    post_coincidence_time = Range(0, 10000, 2000)

    # Read-only attributes below
    gps_latitude = Float()
    gps_longitude = Float()
    gps_altitude = Float()

    ch1_current = Float()
    ch2_current = Float()

    version = Str()

    _device = Value()

    def __init__(self, device):
        super(Config, self).__init__()
        # Keep a weak reference to the device, so the garbage collector
        # can clean up when a device class instance is deleted.
        self._device = weakref.ref(device)

    @observe('ch1_voltage',
             'ch2_voltage',
             'ch1_integrator_time',
             'ch2_integrator_time',
             'ch1_offset_positive',
             'ch1_offset_negative',
             'ch2_offset_positive',
             'ch2_offset_negative',
             'ch1_gain_positive',
             'ch1_gain_negative',
             'ch2_gain_positive',
             'ch2_gain_negative',
             'common_offset',
             'full_scale')
    def _write_byte_setting_to_device(self, setting):
        name, value = setting['name'], setting['value']
        low, high = self._get_range_from(name)
        setting_value = map_setting(value, low, high, 0x00, 0xff)
        msg = SetControlParameter(name, setting_value)
        self._device().send_message(msg)

    @observe('ch1_threshold_low',
             'ch1_threshold_high',
             'ch2_threshold_low',
             'ch2_threshold_high')
    def _write_threshold_setting_to_device(self, setting):
        name, value = setting['name'], setting['value']
        msg = SetControlParameter(name, value, nbytes=2)
        self._device().send_message(msg)

    @observe('pre_coincidence_time',
             'coincidence_time',
             'post_coincidence_time')
    def _write_time_setting_to_device(self, setting):
        name, value = setting['name'], setting['value']
        low, high = self._get_range_from(name)
        # time settings are in 5 ns increments
        setting_value = map_setting(value, low, high, low / 5, high / 5)
        msg = SetControlParameter(name, setting_value, nbytes=2)
        self._device().send_message(msg)

    def _observe_trigger_condition(self, value):
        msg = SetControlParameter('trigger_condition', value['value'])
        self._device().send_message(msg)

    def _observe_one_second_enabled(self, value):
        msg = InitializeMessage(one_second_enabled=value['value'])
        self._device().send_message(msg)

    def _get_range_from(self, name):
        """Get the low, high range from an atom Range object.

        :param name: name of the range attribute
        :returns: (low, high) values of the range

        """
        atom = self.get_member(name)
        validator, (low, high) = atom.validate_mode
        return low, high

    def reset_hardware(self):
        """Force writing all config values to device."""

        settings = self.members()
        for name, setting in settings.iteritems():
            setting.notify(self, {'name': name, 'type': 'update',
                                  'value': getattr(self, name)})

    def update_from_config_message(self, msg):
        """Update read-only config values from hardware config message.

        This updates read-only values from a parameter list returned by the
        hardware device.

        :param msg: ControlParameterList message read from device.

        """
        self.gps_latitude = msg.gps_latitude
        self.gps_longitude = msg.gps_longitude
        self.gps_altitude = msg.gps_altitude

        self.version = "Hardware: %d FPGA: %d" % (msg.serial_number,
                                                  msg.firmware_version)

        self.ch1_current = msg.ch1_current
        self.ch2_current = msg.ch2_current

    def write_config(self, config):
        """Write config settings to existing config object.

        :param config: config object

        """
        section = self._device().description
        if not config.has_section(section):
            config.add_section(section)

        settings = self.members()
        for setting in sorted(settings):
            if setting != '_device':
                config.set(section, setting, getattr(self, setting))

    def read_config(self, config):
        """Read config settings from existing config object.

        :param config: config object

        """
        section = self._device().description
        settings = self.members()
        for setting in settings:
            if setting != '_device':
                try:
                    setting_value = literal_eval(config.get(section, setting))
                except ConfigParser.NoOptionError:
                    # Not found in config file
                    pass
                else:
                    setattr(self, setting, setting_value)
