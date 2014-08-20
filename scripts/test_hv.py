import logging
import os
import zlib
import time

import tables

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs
from pysparc import messages
from pysparc import storage
from pysparc.events import Stew


CONFIGFILE = os.path.expanduser('~/.pysparc')
DATAFILE = 'hisparc.h5'


def timeit(func, *args, **kwargs):
    t0 = time.time()
    ret = func(*args, **kwargs)
    t1 = time.time()
    logging.debug("%s took %.2f s", func.func_name, t1 - t0)
    return ret


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
                '/', 'hisparc', storage.HisparcEvent)
            self.blobs = self.datafile.createVLArray(
                '/', 'blobs', tables.VLStringAtom())

    def run(self):
        # at least two low
        self.device.config.trigger_condition = 0b10
        self.device.config.one_second_enabled = True

        stew = Stew()

        logging.info("Taking data.")
        # Give hardware at least 20 seconds to startup
        t_msg = time.time() + 20
        t_log = time.time() - .5
        try:
            while True:
                t = time.time()
                msg = timeit(self.device.read_message)
                if msg is not None:
                    t_msg = t
                    # logging.debug("Data received: %s", msg)
                    if isinstance(msg, messages.MeasuredDataMessage):
                        timeit(stew.add_event_message, msg)
                    elif isinstance(msg, messages.OneSecondMessage):
                        timeit(stew.add_one_second_message, msg)
                        logging.debug("One-second received: %d", msg.timestamp)
                else:
                    # regretfully required on linux systems
                    time.sleep(.016)
                    if t - t_msg > 5:
                        logging.warning("Hardware is silent, resetting.")
                        self.device.reset_hardware()
                        # Give hardware at least 20 seconds to startup
                        t_msg = t + 20

                if t - t_log >= 1:
                    logging.info("Event rate: %.1f Hz", stew.event_rate())
                    t_log += 1

                    timeit(stew.stir)
                    events = timeit(stew.serve_events)
                    timeit(self.store_events, events)
                    timeit(stew.drain)

        except KeyboardInterrupt:
            logging.info("Interrupted by user.")

    def store_events(self, events):
        for event in events:
            self.store_event(event)
        logging.debug("Stored %d events.", len(events))

    def store_event(self, event):
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

    def close(self):
        logging.info("Writing config to file")
        self.device.config.write_config(CONFIGFILE)
        self.device.close()
        self.datafile.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = Main()
    app.run()
    app.close()
