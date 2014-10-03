"""Classes related to storage of events.

Contents
--------

:class:`StorageError`
    Base error class.
:class:`UploadError`
    Error uploading events.
:class:`IntegrityError`
    Some data is corrupted.

:class:`StorageManager`
    Transparently store events in one or multiple data stores.
:class:`StorageWorker`
    Keep track of events to be stored in a particular datastore.
:class:`HisparcEvent`
    HiSPARC event table description.
:class:`BaseDataStore`
    Base class for storage of HiSPARC events.
:class:`TablesDataStore`
    Datastore for HiSPARC events.
:class:`NikhefDataStore`
    Send events over HTTP to the datastore at Nikhef.

"""

import base64
import cPickle as pickle
import hashlib
import logging
import re
import zlib
import threading
import time

import tables
import requests
from requests.packages.urllib3.exceptions import ProtocolError
from requests import HTTPError
import redis


logger = logging.getLogger(__name__)


DATASTORE_URL = "http://frome.nikhef.nl/hisparc/upload"
SLEEP_INTERVAL = .4


class StorageError(Exception):

    """Base error class."""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "Error storing events (%s)" % self.msg


class UploadError(StorageError):

    """Error uploading events."""

    def __str__(self):
        return "Error uploading events (%s)" % self.msg


class IntegrityError(StorageError):

    """Some data is corrupted."""

    pass


class StorageManager(object):

    """Transparently store events in one or multiple data stores."""

    def __init__(self):
        self.workers = []
        self.kvstore = redis.StrictRedis()

    def add_datastore(self, datastore, queue):
        """Add a datastore to store new events.

        :param datastore: a :class:`BaseDataStore` or derived class instance
        :param queue: a unique name for the queue

        New events will also be stored in the supplied datastore.  A
        unique name for a queue makes it possible to abort a run, change an
        upload URL and restart by specifying the same name for the new
        datastore instance.  Any pending events for the old URL will then
        be send to the new URL.

        """
        worker = StorageWorker(datastore, self.kvstore, queue)
        self.workers.append((queue, worker))

    def store_event(self, event):
        """Add event to queues for storage.

        :param event: a :class:`HisparcEvent` instance.

        The event will be stored in the key-value store and its key
        is added to all queues.  The upload counter is also incremented
        accordingly.

        """

        key = 'event_%d' % event.ext_timestamp
        pickled_event = pickle.dumps(event)
        self.kvstore.hmset(key, {'event': pickled_event, 'count': 0})

        for queue, worker in self.workers:
            self.kvstore.rpush(queue, key)
            self.kvstore.hincrby(key, 'count', 1)


class StorageWorker(threading.Thread):

    """Keep track of events to be stored in a particular datastore."""

    def __init__(self, datastore, kvstore, queue):
        """Instantiate the class.

        :param datastore: DataStore instance which will actually store
            the events.
        :param kvstore: Redis-compatible key-value store which contains
            queue and the events to be stored.
        :param queue: name of the key in the kvstore which contains the
            queue of events to be stored.

        """
        self.datastore = datastore
        self.kvstore = kvstore
        self.queue = queue

    def run(self):
        """Event loop for this worker thread.

        This method is called when the thread is started, and the thread
        will be killed once this method returns.

        """
        pass

    def store_event_or_sleep(self):
        """Store an event from the queue, or sleep.

        Check if there are events in the queue. If so, store one event.
        If not, sleep for a little while (SLEEP_INTERVAL) before
        returning.

        """
        key = self.get_key_from_queue()
        if key:
            self.store_event_by_key(key)
        else:
            time.sleep(SLEEP_INTERVAL)

    def store_event(self):
        """Store an event from the queue in the datastore."""

        key = self.get_key_from_queue()
        if key:
            self.store_event_by_key(key)

    def get_key_from_queue(self):
        """Get first key from queue."""

        return self.kvstore.lindex(self.queue, 0)

    def get_event_by_key(self, key):
        """Get an event from the key-value store referenced by key.

        :param key: key of the event to look up in the key-value store.

        """
        pickled_event = self.kvstore.hget(key, 'event')
        return pickle.loads(pickled_event)

    def store_event_by_key(self, key):
        """Store event referenced by key.

        :param key: key of the event to look up in the key-value store.

        If the event is succesfully stored, remove it from the queue.

        Catch StorageErrors and log them as errors.  Catch all other
        exceptions, but reraise them as StorageErrors, with the original
        exception as string argument.

        """
        event = self.get_event_by_key(key)
        try:
            self.datastore.store_event(event)
        except StorageError as e:
            logger.error(str(e))
        except Exception as e:
            raise StorageError(str(e))
        else:
            self.remove_event_from_queue(key)

    def remove_event_from_queue(self, expected_key):
        """Remove event from queue and decrease upload counter.

        :param expected_key: the expected key to be removed.

        The first element in the queue is removed and compared to the
        expected key.  If they are not equal, an IntegrityError is raised.

        If the upload counter for the event is zero, remove the event
        from the key-value store.

        """
        removed_key = self.kvstore.lpop(self.queue)
        if removed_key != expected_key:
            raise IntegrityError("Key removed from queue is not the expected key.")

        count = self.kvstore.hincrby(expected_key, 'count', -1)
        if count == 0:
            self.kvstore.delete(expected_key)


class HisparcEvent(tables.IsDescription):

    """HiSPARC event table description."""

    event_id = tables.UInt32Col(pos=0)
    timestamp = tables.Time32Col(pos=1)
    nanoseconds = tables.UInt32Col(pos=2)
    ext_timestamp = tables.UInt64Col(pos=3)
    data_reduction = tables.BoolCol(pos=4)
    trigger_pattern = tables.UInt32Col(pos=5)
    baseline = tables.Int16Col(shape=4, dflt=-1, pos=6)
    std_dev = tables.Int16Col(shape=4, dflt=-1, pos=7)
    n_peaks = tables.Int16Col(shape=4, dflt=-1, pos=8)
    pulseheights = tables.Int16Col(shape=4, dflt=-1, pos=9)
    integrals = tables.Int32Col(shape=4, dflt=-1, pos=10)
    traces = tables.Int32Col(shape=4, dflt=-1, pos=11)
    event_rate = tables.Float32Col(pos=12)


class BaseDataStore(object):

    """Base class for storage of HiSPARC events.

    A DataStore is a container for events.  The :meth:`store_event` method
    takes an event and stores it somewhere.  It is up to the
    implementation to decide to store events locally, or over the network.

    """

    def __init__(self):
        """Initialize the datastore.

        Override this method.

        """
        pass

    def store_event(self, event):
        """Store an event.

        Override this method.

        """
        pass

    def close(self):
        """Close the datastore, if necessary.

        Override this method.

        """
        pass


class TablesDataStore(BaseDataStore):

    """Datastore for HiSPARC events.

    Using :meth:`store_event`, HiSPARC events are stored in a HDF5 file
    using PyTables.  The path of the file and the group in which to store
    the events can be specified in the constructor.

    """

    def __init__(self, path, group=None):
        """Initialize the datastore.

        :param path: path of the datafile.
        :param group: group in which to store the events.  If None, a new
            group will be created using the format 'run%d', sequentially
            numbered.

        """
        self.data = tables.openFile(path, 'a')
        if not group:
            group = self._get_new_sequential_group()
        self._create_group_and_tables(group)

        self.events = self.group.events
        self.blobs = self.group.blobs

    def close(self):
        """Close the datastore file."""

        self.data.close()

    def store_event(self, event):
        """Store an event in the datastore.

        :param event: a HiSPARC event.

        """
        row = self.events.row
        row['event_id'] = len(self.events)
        row['timestamp'] = event.timestamp
        row['nanoseconds'] = event.nanoseconds
        row['ext_timestamp'] = event.ext_timestamp
        row['data_reduction'] = event.data_reduction
        row['trigger_pattern'] = event.trigger_pattern
        row['baseline'] = event.baselines
        row['std_dev'] = event.std_dev
        row['n_peaks'] = event.n_peaks
        row['pulseheights'] = event.pulseheights
        row['integrals'] = event.integrals
        row['traces'] = [len(self.blobs), len(self.blobs) + 1, -1, -1]
        self.blobs.append(zlib.compress(','.join([str(int(u)) for u in event.trace_ch1])))
        self.blobs.append(zlib.compress(','.join([str(int(u)) for u in event.trace_ch2])))
        row['event_rate'] = event.event_rate

        row.append()
        self.events.flush()

    def _get_new_sequential_group(self):
        """Create a new group name, sequentially numbered.

        If run1, run3 and run12 are already taken, return run13.  This
        way, if one deletes certain groups, we can always be assured that
        the newest data is in the highest run number.

        """
        run_numbers = []
        for group in self.data.root._v_groups:
            match = re.match('run(\d+)', group)
            if match:
                run_numbers.append(int(match.group(1)))

        try:
            run_number = max(run_numbers) + 1
        except ValueError:
            run_number = 1

        return 'run%d' % run_number

    def _create_group_and_tables(self, group):
        """Create group and tables in HDF5 file.

        :param group: name of the group in which to create the tables.

        """
        self.group = self.data.createGroup('/', group)
        self.data.createTable(self.group, 'events', HisparcEvent)
        self.data.createVLArray(self.group, 'blobs', tables.VLStringAtom())


class NikhefDataStore(object):

    """Send events over HTTP to the datastore at Nikhef.

    A call to :meth:`store_event` will send the event to the datastore at
    Nikhef, using the convoluted datastructure which was created for the
    old eventwarehouse, and still survives to this day.

    """

    def __init__(self, station_id, password):
        """Initialize the datastore.

        Each station has a unique station number / password combination.
        Provide this during initialization.

        """
        self.station_id = station_id
        self.password = password

    def store_event(self, event):
        """Store an event.

        Override this method.

        """
        data = self._create_event_container(event)
        self._upload_data(data)

    def _create_event_container(self, event):
        """Encapsulate an event in a container for the datastore.

        This hurts.  But it is necessary for historical reasons.

        :param event: HiSPARC event object.
        :returns: container for the event data.

        """
        header = {'eventtype_uploadcode': 'CIC',
                  'datetime': event.datetime,
                  'nanoseconds': event.nanoseconds}

        datalist = []
        self._add_value_to_datalist(datalist, 'RED', event.data_reduction)
        self._add_value_to_datalist(datalist, 'EVENTRATE', event.event_rate)
        self._add_value_to_datalist(datalist, 'TRIGPATTERN', event.trigger_pattern)
        self._add_values_to_datalist(datalist, 'BL', event.baselines)
        self._add_values_to_datalist(datalist, 'STDDEV', event.std_dev)
        self._add_values_to_datalist(datalist, 'NP', event.n_peaks)
        self._add_values_to_datalist(datalist, 'PH', event.pulseheights)
        self._add_values_to_datalist(datalist, 'IN', event.integrals)

        # FIXME: no slave support
        trace_ch1 = base64.b64encode(zlib.compress(','.join([str(int(u)) for u in event.trace_ch1])))
        trace_ch2 = base64.b64encode(zlib.compress(','.join([str(int(u)) for u in event.trace_ch2])))
        self._add_values_to_datalist(datalist, 'TR', [trace_ch1, trace_ch2])

        event_list = [{'header': header, 'datalist': datalist}]
        return event_list

    def _add_value_to_datalist(self, datalist, upload_code, value):
        """Add an event value to the datalist.

        :param datalist: datalist object (for upload).
        :param upload_code: the upload code (eg. 'TRIGPATTERN').
        :param value: the value to store in the datalist.

        """
        datalist.append({'data_uploadcode': upload_code,
                         'data': value})

    def _add_values_to_datalist(self, datalist, upload_code, values):
        """Add multiple event values to datalist.

        Takes a list of values and a partial upload code (e.g. 'PH') and
        adds them to the datalist as 'PH1', 'PH2', etc.

        :param datalist: datalist object (for upload).
        :param upload_code: the partial upload code (eg. 'PH').
        :param values: list of values to store in the datalist.

        """
        for idx, value in enumerate(values, 1):
            self._add_value_to_datalist(datalist, upload_code + str(idx),
                                        value)

    def _upload_data(self, data):
        """Upload event data to server.

        :param data: container for the event data.

        """
        pickled_data = pickle.dumps(data)
        checksum = hashlib.md5(pickled_data).hexdigest()

        payload = {'station_id': self.station_id,
                   'password': self.password, 'data': pickled_data,
                   'checksum': checksum}
        try:
            r = requests.post(DATASTORE_URL, data=payload)
            r.raise_for_status()
        except (ProtocolError, HTTPError) as exc:
            raise UploadError(str(exc))
        else:
            logger.debug("Response from server: %s", r.text)
            if r.text != '100':
                raise UploadError("Server responded with error code %s" % r.text)

    def close(self):
        """Close the datastore."""

        pass
