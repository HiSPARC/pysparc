import logging
import ConfigParser
import weakref
from ast import literal_eval

from atom.api import Atom, observe, Range, FloatRange, Value, Bool, Float, Str

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

    # values are in microseconds
    pre_coincidence_time = FloatRange(0., 2., 1.)
    coincidence_time = FloatRange(0., 5., 2.)
    post_coincidence_time = FloatRange(0., 10., 2.)

    # Read-only attributes below
    gps_latitude = Float()
    gps_longitude = Float()
    gps_altitude = Float()

    ch1_current = Float()
    ch2_current = Float()

    version = Str()

    _device = Value()

    _private_settings = ['gps_latitude', 'gps_longitude', 'gps_altitude',
                         'ch1_current', 'ch2_current', 'version']

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
        setting_value = map_setting(value, low, high, low / 5e-3, high / 5e-3)
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

    @classmethod
    def build_trigger_condition(cls, num_low=0, num_high=0, or_not_and=False,
                                use_external=False, calibration_mode=False):
        """Build trigger condition byte from parameters.

        :param num_low: minimum number of detectors over low threshold
        :param num_high: minimum number of detectors over high threshold
        :param or_not_and: if True, condition is num_low OR num_high. If false,
                           condition is num_low AND num_high.
        :param use_external: use external trigger
        :param calibration_mode: trigger once per second, for hardware
                                 calibration.

        :returns: trigger condition, as a coded byte

        """
        if calibration_mode:
            return 1 << 7
        else:
            if not or_not_and:
                trig_condition = num_low + (num_high << 3)
            else:
                trig_condition = 0b100 + (num_low - 1) + (num_high << 3)

            if use_external:
                trig_condition |= 1 << 6

            return trig_condition

    @classmethod
    def unpack_trigger_condition(cls, condition):
        """Unpack trigger condition from byte value.

        :param condition: the trigger condition as a coded byte

        :returns: dictionary with keys describing the trigger condition. The
                  keys are identical to the paramers of the
                  :meth:`build_trigger_condition` method.

        """
        num_low = condition & 0b111
        num_high = (condition & 0b111000) >> 3

        if num_high > 0 and num_low & 0b100:
            or_not_and = True
            num_low = (num_low & 0b11) + 1
        else:
            or_not_and = False

        if condition & (1 << 6):
            use_external = True
        else:
            use_external = False

        if condition & (1 << 7):
            calibration_mode = True
        else:
            calibration_mode = False

        return dict(num_low=num_low, num_high=num_high, or_not_and=or_not_and,
                    use_external=use_external,
                    calibration_mode=calibration_mode)

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

        # 0xff corresponds to 25 mA, give value in mA units
        self.ch1_current = msg.ch1_current * (25. / 0xff)
        self.ch2_current = msg.ch2_current * (25. / 0xff)

        logger.info('Updated config from hardware message')

    def write_config(self, config):
        """Write config settings to existing config object.

        :param config: config object

        """
        section = self._device().description
        if not config.has_section(section):
            config.add_section(section)

        settings = self.members()
        for setting in sorted(settings):
            if setting[0] != '_' and setting not in self._private_settings:
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
