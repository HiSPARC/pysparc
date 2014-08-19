import logging


logger = logging.getLogger(__name__)


class MissingOneSecondMessage(Exception):

    pass


class Stew(object):

    """Prepare events from event and one-second messages."""

    def __init__(self):
        self._event_messages = {}
        self._one_second_messages = {}
        self._events = []

    def add_one_second_message(self, msg):
        """Add a one-second message to the stew.

        :param msg: one-second message

        """
        timestamp = msg.timestamp
        self._one_second_messages[timestamp] = msg

    def add_event_message(self, msg):
        """Add an event message to the stew.

        :param msg: event message

        """
        timestamp = msg.timestamp
        self._event_messages[timestamp] = msg

    def stir(self):
        """Stir stew to mix ingredients.

        For all pending event messages, the necessary one-second messages
        are looked up and the synchronization and quantization errors are
        used to adjust the exact trigger time. Resulting events are ready
        to be served.

        """
        to_be_removed = []

        for timestamp, msg in self._event_messages.iteritems():
            try:
                event = self.cook_event_msg(msg)
            except MissingOneSecondMessage:
                logging.debug("One-second message missing: %s", timestamp)
            else:
                self._events.append(event)
                to_be_removed.append(timestamp)

        for key in to_be_removed:
            del self._event_messages[key]

    def cook_event_msg(self, msg):
        """Cook an event message by correcting the trigger time.

        Analyzing serveral one-second messages, the qunatization errors
        can be used to correct the trigger time.

        :param msg: event message

        :returns: event

        """
        raise MissingOneSecondMessage
        return msg

    def serve_events(self):
        """Serve cooked events.

        Events for which the timestamps are correctly adjusted are served
        and removed from the stew.

        :returns: list of events

        """
        events = self._events
        self._events = []
        return events
