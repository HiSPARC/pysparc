import logging
import os
import zlib
import time
import sys

import tables

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs
from pysparc import messages


CONFIGFILE = os.path.expanduser('~/.pysparc')
DATAFILE = 'hisparc.h5'


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


class Main(object):

    def __init__(self):
        self.device = HiSPARCIII()
        self.initialize_device()
        self.initialize_local_storage()

    def initialize_device(self):
        if not os.path.isfile(CONFIGFILE):
            logging.info("No config file found.  Aligning ADCs.")
            align_adcs = AlignADCs(self.device)
            align_adcs.align()
	    self.device.config.write_config(CONFIGFILE)
        else:
            logging.info("Reading config from file")
            self.device.config.read_config(CONFIGFILE)

    def initialize_local_storage(self):
        self.datafile = tables.openFile(DATAFILE, 'a')
        if '/hisparc' in self.datafile:
            raise RuntimeError("Sorry, I will not overwrite data.  Aborting.")
        else:
            self.events = self.datafile.createTable(
                '/', 'hisparc', HisparcEvent)
            self.blobs = self.datafile.createVLArray(
                '/', 'blobs', tables.VLStringAtom())

    def run(self):
        # at least two low
        self.device.config.trigger_condition = 0b10
        self.device.config.one_second_enabled = True

        try:
            t0 = 0
            t_msg = time.time()
            while True:
                t = time.time()
                if t - t0 > 60:
                    sys.stdout.write(time.ctime())
                    t0 = t

                t1 = time.time()
                msg = self.device.read_message()
                t2 = time.time()
                if t2 - t1 > .020:
                    # read took too long
                    sys.stdout.write('!')
                if msg is not None:
                    t_msg = t
                    logging.info("Data received: %s", msg)
                    if isinstance(msg, messages.MeasuredDataMessage):
                        self.store_event(msg)
                        sys.stdout.write('H')
                    elif isinstance(msg, messages.OneSecondMessage):
                        sys.stdout.write('S')
                    else:
                        sys.stdout.write('?')
                else:
                    time.sleep(.016)
                    sys.stdout.write('.')
                    if t - t_msg > 20:
                        sys.stdout.write('NODATA, RESET')
                        # raise RuntimeError("No data for 60 seconds!")
                        self.device.reset_hardware()
                        t_msg = t
        except KeyboardInterrupt:
            logging.info("Interrupted by user.")

    def store_event(self, msg):
        row = self.events.row
        row['event_id'] = len(self.events)
        row['timestamp'] = msg.timestamp
        row['nanoseconds'] = msg.nanoseconds
        row['ext_timestamp'] = msg.timestamp * int(1e9) + msg.nanoseconds
        row['data_reduction'] = False
        row['trigger_pattern'] = msg.trigger_pattern
        baselines = [msg.trace_ch1[:100].mean(),
                     msg.trace_ch2[:100].mean(), -1, -1]
        row['baseline'] = baselines
        row['std_dev'] = [msg.trace_ch1[:100].std(),
                          msg.trace_ch2[:100].std(), -1, -1]
        row['n_peaks'] = 4 * [-999]
        row['pulseheights'] = [msg.trace_ch1.max() - baselines[0],
                               msg.trace_ch2.max() - baselines[1], -1, -1]
        row['integrals'] = 4 * [-999]
        row['traces'] = [len(self.blobs), len(self.blobs) + 1, -1, -1]
        self.blobs.append(zlib.compress(','.join([str(int(u)) for u in msg.trace_ch1])))
        self.blobs.append(zlib.compress(','.join([str(int(u)) for u in msg.trace_ch2])))
        row['event_rate'] = -1

        row.append()
        self.events.flush()

    def close(self):
        logging.info("Writing config to file")
        self.device.config.write_config(CONFIGFILE)
        self.device.close()
        self.datafile.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    app = Main()
    app.run()
    app.close()
