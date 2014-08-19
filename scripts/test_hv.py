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
                msg = self.device.read_message()
                if msg is not None:
                    t_msg = t
                    # logging.debug("Data received: %s", msg)
                    if isinstance(msg, messages.MeasuredDataMessage):
                        stew.add_event_message(msg)
                    elif isinstance(msg, messages.OneSecondMessage):
                        stew.add_one_second_message(msg)
                else:
                    # regretfully required on linux systems
                    time.sleep(.016)
                    if t - t_msg > 5:
                        logging.warning("Hardware is silent, resetting.")
                        self.device.reset_hardware()
                        # Give hardware at least 20 seconds to startup
                        t_msg = t + 20
                stew.stir()
                events = stew.serve_events()
                for event in events:
                    self.store_event(event)

                if t - t_log >= 1:
                    logging.debug("Stew size: %d %d",
                                 len(stew._one_second_messages),
                                 len(stew._event_messages))
                    t_log += 1
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
    logging.basicConfig(level=logging.DEBUG)
    app = Main()
    app.run()
    app.close()
