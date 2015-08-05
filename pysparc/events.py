from __future__ import division

import collections
import logging
import time
import zlib

import numpy as np
from lazy import lazy


logger = logging.getLogger(__name__)


# After 10 s, messages are no longer fresh
FRESHNESS_TIME = 10
# Number of seconds over which to average event rate
EVENTRATE_TIME = 60

SYNCHRONIZATION_BIT = 1 << 31
NANOSECONDS_PER_SECOND = int(1e9)

INTEGRAL_THRESHOLD = 25


class MissingOneSecondMessage(Exception):

    pass


class Stew(object):

    """Prepare events from event and one-second messages."""

    def __init__(self):
        self._event_messages = {}
        self._one_second_messages = {}
        self._events = []
        self._latest_timestamp = 0
        self._event_rates = collections.defaultdict(lambda: 0)

    def add_one_second_message(self, msg):
        """Add a one-second message to the stew.

        The timestamp is used to keep track of the freshness of messages.

        :param msg: one-second message

        """
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
        CTP = t1_msg.count_ticks_PPS
        synchronization_error = 2.5 if (t0_msg.count_ticks_PPS & SYNCHRONIZATION_BIT) else 0
        quantization_error1 = t1_msg.quantization_error * 1e9
        quantization_error2 = t2_msg.quantization_error * 1e9

        # This may be larger than one second due to synchronization error!
        trigger_offset = int(synchronization_error + quantization_error1
                             + (CTD / CTP)
                             * (1e9 - quantization_error1 + quantization_error2))
        ext_timestamp = msg.timestamp * NANOSECONDS_PER_SECOND + trigger_offset

        # Correct timestamp
        msg.timestamp = int(ext_timestamp / NANOSECONDS_PER_SECOND)
        msg.nanoseconds = ext_timestamp % NANOSECONDS_PER_SECOND
        msg.ext_timestamp = ext_timestamp

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

        try:
            number_of_events = sum(self._event_rates.values())
            timestamps = self._event_rates.keys()
            time = EVENTRATE_TIME
            event_rate = number_of_events / time
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
                logger.warning("Perished; draining event message: %d", timestamp)
                del self._event_messages[key]

        for timestamp in self._event_rates.keys():
            if self._latest_timestamp - timestamp > EVENTRATE_TIME:
                logger.debug("Draining stale event rate value: %d", timestamp)
                del self._event_rates[timestamp]


class Event(object):

    """A HiSPARC event, with preliminary analysis."""

    def __init__(self, msg, event_rate=-1):
        self._msg = msg

        self.datetime = msg.datetime
        self.timestamp = msg.timestamp
        self.nanoseconds = msg.nanoseconds
        self.ext_timestamp = msg.timestamp * int(1e9) + msg.nanoseconds
        self.data_reduction = False
        self.trigger_pattern = msg.trigger_pattern
        self.event_rate = event_rate

        # Not yet implemented
        self.n_peaks = 4 * [-999]

        ## Formerly lazy attributes

        # Traces
        self.trace_ch1 = self._msg.trace_ch1
        self.trace_ch2 = self._msg.trace_ch2

        # Compressed traces
        self.zlib_trace_ch1 = zlib.compress(','.join([str(int(u)) for u in self.trace_ch1]))
        self.zlib_trace_ch2 = zlib.compress(','.join([str(int(u)) for u in self.trace_ch2]))

        # Mean value of the first 100 samples of the trace
        baselines = [int(round(t[:100].mean())) for t in self.trace_ch1, self.trace_ch2]
        self.baselines = baselines + [-1, -1]

        # Standard deviation of the first 100 samples of the trace
        std_dev = [int(round(t[:100].std())) for t in self.trace_ch1, self.trace_ch2]
        self.std_dev = std_dev + [-1, -1]

        # Maximum peak to baseline value in trace
        self.pulseheights = [self.trace_ch1.max() - self.baselines[0],
                             self.trace_ch2.max() - self.baselines[1],
                             -1, -1]

        # Integral of trace for all values over threshold
        # The threshold is defined by INTEGRAL_THRESHOLD
        traces = np.vstack([self.trace_ch1, self.trace_ch2])
        baselines = np.array([self.baselines[:2]])
        traces -= baselines.T
        integrals = [t.compress(t > INTEGRAL_THRESHOLD).sum() for t in traces]
        self.integrals = integrals + [-1, -1]


class ConfigEvent(object):

    def __init__(self, app_config, master_config):
        self.pre_coincidence_time = master_config.pre_coincidence_time
        self.coincidence_time = master_config.coincidence_time
        self.post_coincidence_time = master_config.post_coincidence_time

        self.use_filter = False
        self.use_filter_threshold = False
        self.reduce_data = False

        self.mas_ch1_thres_low = master_config.ch1_threshold_low
        self.mas_ch1_thres_high = master_config.ch1_threshold_high
        self.mas_ch2_thres_low = master_config.ch2_threshold_low
        self.mas_ch2_thres_high = master_config.ch2_threshold_high

        self.mas_ch1_voltage = master_config.ch1_voltage
        self.mas_ch2_voltage = master_config.ch2_voltage

        self.mas_ch1_offset_pos = master_config.ch1_offset_positive
        self.mas_ch1_offset_neg = master_config.ch1_offset_negative
        self.mas_ch2_offset_pos = master_config.ch2_offset_positive
        self.mas_ch2_offset_neg = master_config.ch2_offset_negative
        self.mas_ch1_gain_pos = master_config.ch1_gain_positive
        self.mas_ch1_gain_neg = master_config.ch1_gain_negative
        self.mas_ch2_gain_pos = master_config.ch2_gain_positive
        self.mas_ch2_gain_neg = master_config.ch2_gain_negative
        self.mas_common_offset = master_config.common_offset
        self.mas_internal_voltage = master_config.full_scale
