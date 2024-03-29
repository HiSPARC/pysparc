from __future__ import division

import collections
import datetime
import logging
import time
import zlib

import numpy as np


logger = logging.getLogger(__name__)


# After 10 s, messages are no longer fresh
FRESHNESS_TIME = 10
# Number of seconds over which to average event rate
EVENTRATE_TIME = 60
# Maximum allowed time difference between primary and secondary events
MAX_FOUR_CHANNEL_DELAY = 5000

SYNCHRONIZATION_BIT = 1 << 31
CTP_BITS = (1 << 31) - 1
NANOSECONDS_PER_SECOND = int(1e9)

INTEGRAL_THRESHOLD = 25
# default low threshold for signals (approx. 30 mV above baseline)
PEAK_THRESHOLD = 50


class MissingOneSecondMessage(Exception):

    pass


class Stew(object):

    """Prepare events from event and one-second messages."""

    def __init__(self):
        self._event_messages = {}
        self._one_second_messages = {}
        self._events = []
        self._latest_timestamp = 0
        # Setting the defaultfactory to 0. This allows adding values to
        # non-existing keys, like d[key] += 1 if key does not exist.
        self._event_rates = collections.defaultdict(lambda: 0)
        self._last_update = 0

    def add_one_second_message(self, msg):
        """Add a one-second message to the stew.

        The timestamp is used to keep track of the freshness of messages.

        :param msg: one-second message

        """
        self._last_update = time.time()
        timestamp = msg.timestamp
        delta_t = timestamp - self._latest_timestamp

        logger.debug("_latest_timestamp %d, timestamp %d, delta_t %d",
                     self._latest_timestamp, timestamp, delta_t)

        # Keep track of latest timestamp and log problems
        if delta_t < 0:
            # out of order, do not set _latest_timestamp
            logger.warning("One-second messages are out of order.")
        else:
            if self._latest_timestamp == 0:
                # this was the first message received, skip checks
                pass
            elif abs(delta_t) > FRESHNESS_TIME:
                # recover from very late or very early messages
                logger.error("One-second messages delta_t very large "
                             "(%d), trying to recover", delta_t)
            elif delta_t > 1:
                for t in range(self._latest_timestamp + 1, timestamp):
                    logger.warning(
                        "Probably missing one-second message: %d", t)
            # store latest timestamp
            self._latest_timestamp = timestamp

        # store message
        self._one_second_messages[timestamp] = msg

    def add_event_message(self, msg):
        """Add an event message to the stew.

        :param msg: event message

        """
        self._last_update = time.time()
        if not self._one_second_messages:
            logger.debug("No one-second messages yet, ignoring event.")
        else:
            self._event_messages[msg.ext_timestamp] = msg
            self._event_rates[msg.timestamp] += 1

    def stir(self):
        """Stir stew to mix ingredients.

        For all pending event messages, the necessary one-second messages
        are looked up and the synchronization and quantization errors are
        used to adjust the exact trigger time. If all the necessary
        ingredients are in the stew,  resulting events are ready to be
        served.

        """
        for key, msg in self._event_messages.items():
            try:
                event = self.cook_event_msg(msg)
            except MissingOneSecondMessage:
                pass
            else:
                self._events.append(event)
                del self._event_messages[key]

    def cook_event_msg(self, msg):
        """Cook an event message by correcting the trigger time.

        Analyzing serveral one-second messages, the quantization errors
        can be used to correct the trigger time.

        :param msg: event message

        :returns: event

        """
        t0_msg = self._get_one_second_message(msg.timestamp)
        t1_msg = self._get_one_second_message(msg.timestamp + 1)
        t2_msg = self._get_one_second_message(msg.timestamp + 2)

        CTD = msg.count_ticks_PPS
        # CTP is everything EXCEPT the synchronization bit
        CTP = t1_msg.count_ticks_PPS & CTP_BITS
        synchronization_error = 2.5 if (t0_msg.count_ticks_PPS &
                                        SYNCHRONIZATION_BIT) else 0
        # ERROR IN TRIMBLE/HISPARC DOCS: quantization error is in NANOseconds
        quantization_error1 = t1_msg.quantization_error
        quantization_error2 = t2_msg.quantization_error

        # This may be larger than one second due to synchronization error!
        trigger_offset = int(synchronization_error + quantization_error1
                             + (CTD / CTP)
                             * (1e9 - quantization_error1 +
                                quantization_error2))
        ext_timestamp = msg.timestamp * NANOSECONDS_PER_SECOND + trigger_offset

        # Synchronize with LabVIEW DAQ. There is a one-second difference
        # between LabVIEW DAQ and PySPARC. We don't know why.
        ext_timestamp += 1 * NANOSECONDS_PER_SECOND

        # Correct timestamp (and datetime attribute)
        msg.timestamp = int(ext_timestamp / NANOSECONDS_PER_SECOND)
        msg.nanoseconds = ext_timestamp % NANOSECONDS_PER_SECOND
        msg.ext_timestamp = ext_timestamp
        msg.datetime = datetime.datetime.utcfromtimestamp(msg.timestamp)

        logger.debug("Event message cooked, timestamp: %d", msg.timestamp)
        return Event(msg)

    def _get_one_second_message(self, timestamp):
        """Return one-second message or raise MissingOneSecondMessage.

        :param timestamp: timestamp of the one-second message

        """
        try:
            return self._one_second_messages[timestamp]
        except KeyError:
            raise MissingOneSecondMessage(
                "One-second message not (yet) received.")

    def serve_events(self):
        """Serve cooked events.

        Events for which the timestamps are correctly adjusted are served
        and removed from the stew.

        :returns: list of events

        """
        events = self._events
        self._events = []
        return events

    def event_rate(self):
        """Return event rate, averaged over EVENTRATE_TIME seconds."""

        # if the hardware fell silent, return 0.0
        if time.time() - self._last_update > FRESHNESS_TIME:
            return -999.0

        try:
            number_of_events = sum(self._event_rates.values())
            event_rate = number_of_events / EVENTRATE_TIME
            return event_rate
        except (ValueError, ZeroDivisionError):
            # probably there are no events received yet in more than one
            # second
            return 0.0

    def drain(self):
        """Drain stale event and one-second messages from stew.

        Event and one-second messages which are no longer fresh (ie. their
        timestamp is a long time in the past) are removed from the stew.

        """
        for timestamp in self._one_second_messages.keys():
            if self._latest_timestamp - timestamp > FRESHNESS_TIME:
                logger.debug("Draining one-second message: %d", timestamp)
                del self._one_second_messages[timestamp]

        for key, msg in self._event_messages.items():
            timestamp = msg.timestamp
            if self._latest_timestamp - timestamp > FRESHNESS_TIME:
                logger.warning("Perished; draining event message: %d",
                               timestamp)
                del self._event_messages[key]

        for timestamp in self._event_rates.keys():
            if self._latest_timestamp - timestamp > EVENTRATE_TIME:
                logger.debug("Draining stale event rate value: %d", timestamp)
                del self._event_rates[timestamp]


class Mixer(object):

    def __init__(self):
        self._primary_events = {}
        self._secondary_events = {}
        self._mixed_events = []

    def add_primary_events(self, events):
        for event in events:
            self._primary_events[event.ext_timestamp] = event

    def add_secondary_events(self, events):
        for event in events:
            self._secondary_events[event.ext_timestamp] = event

    def serve_events(self):
        events = self._mixed_events
        self._mixed_events = []
        return events

    def drain(self):
        pass

    def mix(self):
        primary_timestamps = self._primary_events.keys()
        if primary_timestamps:
            for timestamp, secondary_event in self._secondary_events.items():
                delta_t = [abs(u - timestamp) for u in primary_timestamps]
                min_delta_t = min(delta_t)

                if min_delta_t < MAX_FOUR_CHANNEL_DELAY:
                    primary_idx = delta_t.index(min_delta_t)
                    nearest_timestamp = primary_timestamps[primary_idx]
                    primary_event = self._primary_events[nearest_timestamp]

                    mixed_event = FourChannelEvent(primary_event, secondary_event)
                    self._mixed_events.append(mixed_event)

                    del self._secondary_events[timestamp]
                    del self._primary_events[nearest_timestamp]


class Event(object):

    """A HiSPARC event, with preliminary analysis."""

    def __init__(self, msg, event_rate=-1):
        self._msg = msg

        self.datetime = msg.datetime
        self.timestamp = msg.timestamp
        self.nanoseconds = msg.nanoseconds
        self.ext_timestamp = msg.ext_timestamp
        self.data_reduction = False
        self.trigger_pattern = msg.trigger_pattern
        self.event_rate = event_rate

        # Traces
        self.trace_ch1 = self._msg.trace_ch1
        self.trace_ch2 = self._msg.trace_ch2

        # Compressed traces
        self.zlib_trace_ch1 = zlib.compress(','.join([str(int(u)) for u in
                                                      self.trace_ch1]))
        self.zlib_trace_ch2 = zlib.compress(','.join([str(int(u)) for u in
                                                      self.trace_ch2]))

        # Mean value of the first 100 samples of the trace
        baselines = [int(round(t[:100].mean())) for t in (self.trace_ch1,
                                                          self.trace_ch2)]
        self.baselines = baselines + [-1, -1]

        # Standard deviation of the first 100 samples of the trace
        std_dev = [int(round(1000 * t[:100].std())) for t in (self.trace_ch1,
                                                              self.trace_ch2)]
        self.std_dev = std_dev + [-1, -1]

        # Maximum peak to baseline value in trace
        self.pulseheights = [self.trace_ch1.max() - self.baselines[0],
                             self.trace_ch2.max() - self.baselines[1],
                             -1, -1]

        self.integrals = self._calculate_integral_of_traces() + [-1, -1]

        self.n_peaks = self._calculate_n_peaks() + [-1, -1]

    def _calculate_integral_of_traces(self):
        """Calculate integral of trace for all values over threshold.

        The threshold is defined by INTEGRAL_THRESHOLD.

        """
        traces = np.vstack([self.trace_ch1, self.trace_ch2])
        baselines = np.array([self.baselines[:2]])
        traces -= baselines.T
        integrals = [t.compress(t > INTEGRAL_THRESHOLD).sum() for t in traces]
        return integrals

    def _calculate_n_peaks(self):
        """Calculate number of peaks in traces."""

        n_peaks = []
        for trace, baseline in zip([self.trace_ch1, self.trace_ch2],
                                   self.baselines):
            n_peak = 0
            in_peak = False
            local_minimum = 0
            peak_threshold = PEAK_THRESHOLD + baseline
            for value in trace:
                if not in_peak:
                    if value < local_minimum:
                        local_minimum = value if value > 0 else 0
                    elif value - local_minimum > peak_threshold:
                        # enough signal over local minimum to be in a peak
                        in_peak = True
                        local_maximum = value
                        n_peak += 1
                else:
                    if value > local_maximum:
                        local_maximum = value
                    elif local_maximum - value > peak_threshold:
                        # enough signal decrease to be out of peak
                        in_peak = False
                        local_minimum = value if value > 0 else 0
            n_peaks.append(n_peak)

        return n_peaks


class FourChannelEvent(Event):

    def __init__(self, primary_event, secondary_event):
        self.datetime = primary_event.datetime
        self.timestamp = primary_event.timestamp
        self.nanoseconds = primary_event.nanoseconds
        self.ext_timestamp = primary_event.ext_timestamp
        self.data_reduction = False
        self.trigger_pattern = primary_event.trigger_pattern
        self.event_rate = primary_event.event_rate

        # Traces
        self.trace_ch1 = primary_event.trace_ch1
        self.trace_ch2 = primary_event.trace_ch2
        self.trace_ch3 = secondary_event.trace_ch1
        self.trace_ch4 = secondary_event.trace_ch2

        # Compressed traces
        self.zlib_trace_ch1 = primary_event.zlib_trace_ch1
        self.zlib_trace_ch2 = primary_event.zlib_trace_ch2
        self.zlib_trace_ch3 = secondary_event.zlib_trace_ch1
        self.zlib_trace_ch4 = secondary_event.zlib_trace_ch2

        # Calculated statistics
        self.baselines = primary_event.baselines[:2] + secondary_event.baselines[:2]
        self.std_dev = primary_event.std_dev[:2] + secondary_event.std_dev[:2]
        self.pulseheights = primary_event.pulseheights[:2] + \
            secondary_event.pulseheights[:2]
        self.integrals = primary_event.integrals[:2] + secondary_event.integrals[:2]
        self.n_peaks = primary_event.n_peaks[:2] + secondary_event.n_peaks[:2]


class ConfigEvent(object):

    def __init__(self, primary_config, secondary_config=None):
        self.pre_coincidence_time = primary_config.pre_coincidence_time
        self.coincidence_time = primary_config.coincidence_time
        self.post_coincidence_time = primary_config.post_coincidence_time

        self.gps_latitude = primary_config.gps_latitude
        self.gps_longitude = primary_config.gps_longitude
        self.gps_altitude = primary_config.gps_altitude

        self.use_filter = False
        self.use_filter_threshold = False
        self.reduce_data = False

        condition = primary_config.unpack_trigger_condition(
            primary_config.trigger_condition)
        self.trig_low_signals = condition['num_low']
        self.trig_high_signals = condition['num_high']
        self.trig_or_not_and = condition['or_not_and']
        self.trig_external = condition['use_external']

        self.mas_version = primary_config.version
        self.mas_ch1_current = primary_config.ch1_current
        self.mas_ch2_current = primary_config.ch2_current

        self.mas_ch1_thres_low = primary_config.ch1_threshold_low
        self.mas_ch1_thres_high = primary_config.ch1_threshold_high
        self.mas_ch2_thres_low = primary_config.ch2_threshold_low
        self.mas_ch2_thres_high = primary_config.ch2_threshold_high

        self.mas_ch1_voltage = primary_config.ch1_voltage
        self.mas_ch2_voltage = primary_config.ch2_voltage

        self.mas_ch1_inttime = primary_config.ch1_integrator_time
        self.mas_ch2_inttime = primary_config.ch2_integrator_time

        self.mas_ch1_offset_pos = primary_config.ch1_offset_positive
        self.mas_ch1_offset_neg = primary_config.ch1_offset_negative
        self.mas_ch2_offset_pos = primary_config.ch2_offset_positive
        self.mas_ch2_offset_neg = primary_config.ch2_offset_negative
        self.mas_ch1_gain_pos = primary_config.ch1_gain_positive
        self.mas_ch1_gain_neg = primary_config.ch1_gain_negative
        self.mas_ch2_gain_pos = primary_config.ch2_gain_positive
        self.mas_ch2_gain_neg = primary_config.ch2_gain_negative
        self.mas_common_offset = primary_config.common_offset
        self.mas_internal_voltage = primary_config.full_scale

        if secondary_config is None:
            self.slv_version = "Hardware: 0 FPGA: 0"
        else:
            self.slv_version = secondary_config.version
            self.slv_ch1_current = secondary_config.ch1_current
            self.slv_ch2_current = secondary_config.ch2_current

            self.slv_ch1_thres_low = secondary_config.ch1_threshold_low
            self.slv_ch1_thres_high = secondary_config.ch1_threshold_high
            self.slv_ch2_thres_low = secondary_config.ch2_threshold_low
            self.slv_ch2_thres_high = secondary_config.ch2_threshold_high

            self.slv_ch1_voltage = secondary_config.ch1_voltage
            self.slv_ch2_voltage = secondary_config.ch2_voltage

            self.slv_ch1_inttime = secondary_config.ch1_integrator_time
            self.slv_ch2_inttime = secondary_config.ch2_integrator_time

            self.slv_ch1_offset_pos = secondary_config.ch1_offset_positive
            self.slv_ch1_offset_neg = secondary_config.ch1_offset_negative
            self.slv_ch2_offset_pos = secondary_config.ch2_offset_positive
            self.slv_ch2_offset_neg = secondary_config.ch2_offset_negative
            self.slv_ch1_gain_pos = secondary_config.ch1_gain_positive
            self.slv_ch1_gain_neg = secondary_config.ch1_gain_negative
            self.slv_ch2_gain_pos = secondary_config.ch2_gain_positive
            self.slv_ch2_gain_neg = secondary_config.ch2_gain_negative
            self.slv_common_offset = secondary_config.common_offset
            self.slv_internal_voltage = secondary_config.full_scale
