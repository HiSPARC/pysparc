from array import array

import pylibftdi

from pysparc.util import map_setting


DESCRIPTION = "USB <-> Serial"


class MuonlabII:

    # Yes, really, HV1 and 2 are reversed
    _address = {'HV_1': 2,
                'HV_2': 1,
                'THR_1': 3,
                'THR_2': 4,
                'MEAS': 5,
              }

    def __init__(self):
        self._device = pylibftdi.Device(DESCRIPTION)

    def write_setting(self, setting, data):
        """write setting to device.

        :param setting: string specifying the setting to write.  Must be
            one of HV_1 (for PMT 1 high voltage), HV_2 (for PMT 2 high
            voltage), THR_1 (for PMT 1 threshold), THR_2 (for PMT 2
            threshold) or MEAS (for type of measurement).
        :param data: the raw data byte to write to the device.

        For a high voltage setting, the data byte values (in the range of
        0x00 - 0xff) are mapped linearly to 300 - 1500 V.  For a threshold
        setting, the data byte values (0x00 - 0xff) are linearly mapped to
        0 mV - 1200 mV.

        The type of measurement can be set using only 4 bits.  They must
        be 0b1111 for a muon lifetime measurement.  Any other value will
        select a coincidence time difference measurement.

        """

        if setting not in self._address:
            raise TypeError("Unkown setting: %s" % setting)
        else:
            address_bits = self._address[setting]

        high_byte = (1 << 7) + (address_bits << 4) + ((data & 0xf0) >> 4)
        low_byte = (0 << 7) + (address_bits << 4) + (data & 0x0f)
        command = array('B', [high_byte, low_byte]).tostring()
        self._device.write(command)

    def _set_pmt1_voltage(self, voltage):
        """set high voltage for PMT 1.

        :param voltage: integer.  Values are clipped to a 300 - 1500 V
            range.

        """
        voltage_byte = map_setting(voltage, 300, 1500, 0x00, 0xff)
        self.write_setting('HV_1', voltage_byte)

    def _set_pmt2_voltage(self, voltage):
        """set high voltage for PMT 2.

        :param voltage: integer.  Values are clipped to a 300 - 1500 V
            range.

        """
        voltage_byte = map_setting(voltage, 300, 1500, 0x00, 0xff)
        self.write_setting('HV_2', voltage_byte)

    def _set_pmt1_threshold(self, threshold):
        """set threshold for PMT 1.

        Events with a signal strength below the specified threshold will
        be ignored as noise.

        :param threshold: integer.  Values are clipped to a 0 - 1200 mV
            range.

        """
        threshold_byte = map_setting(threshold, 0, 1200, 0x00, 0xff)
        self.write_setting('THR_1', threshold_byte)

    def _set_pmt2_threshold(self, threshold):
        """set threshold for PMT 2.

        Events with a signal strength below the specified threshold will
        be ignored as noise.

        :param threshold: integer.  Values are clipped to a 0 - 1200 mV
            range.

        """
        threshold_byte = map_setting(threshold, 0, 1200, 0x00, 0xff)
        self.write_setting('THR_2', threshold_byte)
