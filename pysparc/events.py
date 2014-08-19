import logging


logger = logging.getLogger(__name__)


# After 10 s, messages are no longer fresh
FRESHNESS_TIME = 10


class MissingOneSecondMessage(Exception):

    pass


class Stew(object):

    """Prepare events from event and one-second messages."""

    def __init__(self):
        self._event_messages = {}
        self._one_second_messages = {}
        self._events = []
        self._latest_timestamp = 0

    def add_one_second_message(self, msg):
        """Add a one-second message to the stew.

        The timestamp is used to keep track of the freshness of messages.

        :param msg: one-second message

        """
        timestamp = msg.timestamp
        delta_t = timestamp - self._latest_timestamp

        if delta_t > 0:
            if delta_t > 1:
                if self._latest_timestamp:
                    # if not, this was the first message received
                    for t in range(self._latest_timestamp + 1, timestamp):
                        logger.warning(
                            "Probably missing one-second message: %d", t)
            self._latest_timestamp = timestamp
        elif delta_t < 0:
            logger.warning("One-second messages are out of order.")
        else:
            logger.error("Seriously strange problem with one-second messages!")
        self._one_second_messages[timestamp] = msg

    def add_event_message(self, msg):
        """Add an event message to the stew.

        :param msg: event message

        """
        self._event_messages[msg.ext_timestamp] = msg

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

        Analyzing serveral one-second messages, the qunatization errors
        can be used to correct the trigger time.

        :param msg: event message

        :returns: event

        """
        t0_msg = self._get_one_second_message(msg.timestamp)
        t1_msg = self._get_one_second_message(msg.timestamp + 1)
        t2_msg = self._get_one_second_message(msg.timestamp + 2)
        # WIP
        logger.debug("Event message cooked, timestamp: %d", msg.timestamp)
        return msg

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

    def drain(self):
        """Drain stale event and one-second messages from stew.

        Event and one-second messages which are no longer fresh (ie. their
        timestamp is a long time in the past) are removed from the stew.

        """
        for timestamp, msg in self._one_second_messages.items():
            if self._latest_timestamp - timestamp > FRESHNESS_TIME:
                logger.debug("Draining one-second message: %d", timestamp)
                del self._one_second_messages[timestamp]

        for key, msg in self._event_messages.items():
            timestamp = msg.timestamp
            if self._latest_timestamp - timestamp > FRESHNESS_TIME:
                logger.debug("Perished; draining event message: %d", timestamp)
                del self._event_messages[key]
