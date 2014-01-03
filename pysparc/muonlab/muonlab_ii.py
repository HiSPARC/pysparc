from array import array

import pylibftdi

from pysparc.util import map_setting


DESCRIPTION = "USB <-> Serial"

# FTDI documentation: must be multiple of block size, which is 64 bytes
# with 2 bytes overhead.  So, must be multiple of 62 bytes.
READ_SIZE = 62

# Default buffer size is 4K (64 * 64 bytes), but mind the overhead
BUFFER_SIZE = 64 * 62

LIFETIME_SCALE = 6.25
COINCIDENCE_TIMEDELTA_SCALE = 6.25 / 12


class MuonlabII:

    # Yes, really, HV1 and 2 are reversed
    _address = {'HV_1': 2,
                'HV_2': 1,
                'THR_1': 3,
                'THR_2': 4,
                'MEAS': 5}

    def __init__(self):
        self._device = pylibftdi.Device(DESCRIPTION)

    def __del__(self):
        """Cleanly shut down muonlab hardware."""

        self._set_pmt1_voltage(0)
        self._set_pmt2_voltage(0)
        self._device.close()

    def _write_setting(self, setting, data):
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

        high_byte = (1 << 7) | (address_bits << 4) | ((data & 0xf0) >> 4)
        low_byte = (address_bits << 4) | (data & 0x0f)

        if setting == 'MEAS':
            # Measurement type can be selected using only 1 byte
            command = chr(low_byte)
        else:
            command = array('B', [high_byte, low_byte]).tostring()
        self._device.write(command)

    def _set_pmt1_voltage(self, voltage):
        """set high voltage for PMT 1.

        :param voltage: integer.  Values are clipped to a 300 - 1500 V
            range.

        """
        voltage_byte = map_setting(voltage, 300, 1500, 0x00, 0xff)
        self._write_setting('HV_1', voltage_byte)

    def _set_pmt2_voltage(self, voltage):
        """set high voltage for PMT 2.

        :param voltage: integer.  Values are clipped to a 300 - 1500 V
            range.

        """
        voltage_byte = map_setting(voltage, 300, 1500, 0x00, 0xff)
        self._write_setting('HV_2', voltage_byte)

    def _set_pmt1_threshold(self, threshold):
        """set threshold for PMT 1.

        Events with a signal strength below the specified threshold will
        be ignored as noise.

        :param threshold: integer.  Values are clipped to a 0 - 1200 mV
            range.

        """
        threshold_byte = map_setting(threshold, 0, 1200, 0x00, 0xff)
        self._write_setting('THR_1', threshold_byte)

    def _set_pmt2_threshold(self, threshold):
        """set threshold for PMT 2.

        Events with a signal strength below the specified threshold will
        be ignored as noise.

        :param threshold: integer.  Values are clipped to a 0 - 1200 mV
            range.

        """
        threshold_byte = map_setting(threshold, 0, 1200, 0x00, 0xff)
        self._write_setting('THR_2', threshold_byte)

    def _set_lifetime_measurement(self):
        """select lifetime measurement mode"""

        self._write_setting('MEAS', 0xff)

    def _set_coincidence_measurement(self):
        """select coincidence time difference measurement mode"""

        self._write_setting('MEAS', 0x00)

    def flush_device(self):
        """Flush device output buffers.

        To completely clear out outdated measurements when changing
        parameters, call this method.  All data received after this method
        was called is really newly measured.

        """
        self._device.flush_output()
        self._device.read(BUFFER_SIZE)

    def read_lifetime_data(self):
        """Read lifetime data from detector

        :returns: list of lifetime measurements

        """
        data = self._device.read(READ_SIZE)

        if data:
            lifetimes = []
            #for word_value in data[::2]:
            for i in range(0, len(data), 2):
                high_byte, low_byte = ord(data[i]), ord(data[i + 1])

                # sanity checks
                if not (high_byte & 0x80):
                    raise ValueError(
                        "Corrupt lifetime data (high byte bit flag not set)")
                if (low_byte & 0x80):
                    raise ValueError(
                        "Corrupt lifetime data (low byte bit flag set)")

                adc_value = ((high_byte & 0x3f) << 6) | (low_byte & 0x3f)
                lifetime = LIFETIME_SCALE * adc_value
                lifetimes.append(lifetime)
            return lifetimes
        else:
            return []

    def read_coincidence_data(self):
        """Read coincidence data from detector

        :returns: list of coincidence time difference measurements

        """
        data = self._device.read(READ_SIZE)
        if data:
            deltatimes = []
            #for word_value in data[::2]:
            for i in range(0, len(data), 2):
                high_byte, low_byte = ord(data[i]), ord(data[i + 1])

                det1_firsthit = high_byte & 0x40
                det2_firsthit = low_byte & 0x40

                # sanity checks
                if not (high_byte & 0x80):
                    raise ValueError("Corrupt coincidence data "
                                     "(high byte bit flag not set)")
                if (low_byte & 0x80):
                    raise ValueError(
                        "Corrupt coincidence data (low byte bit flag set)")
                if not det1_firsthit and not det2_firsthit:
                    raise ValueError(
                        "Corrupt coincidence data (no hit first flag set)")

                adc_value = ((high_byte & 0x3f) << 6) | (low_byte & 0x3f)
                deltatime = COINCIDENCE_TIMEDELTA_SCALE * adc_value
                if det2_firsthit:
                    deltatime *= -1
                deltatimes.append(deltatime)
            return deltatimes
        else:
            return []
