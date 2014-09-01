"""Classes related to storage of events."""


import re
import zlib

import tables


class HisparcEvent(tables.IsDescription):
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
