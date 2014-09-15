import logging
import os
import time
import ConfigParser

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs
from pysparc.events import Stew
from pysparc import messages, storage, monitor


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
        self.config = ConfigParser.ConfigParser()
        self.device = HiSPARCIII()
        self.initialize_device()
        self.datastore = storage.TablesDataStore(DATAFILE)
        #self.datastore = storage.NikhefDataStore(599, 'pysparc')
        self.monitor = monitor.Monitor('hostname')

    def initialize_device(self):
        if not os.path.isfile(CONFIGFILE):
            logging.info("No config file found.  Aligning ADCs.")
            align_adcs = AlignADCs(self.device)
            align_adcs.align()
            self.write_config()
        else:
            logging.info("Reading config from file")
            self.config.read(CONFIGFILE)
            self.device.config.read_config(self.config)

    def run(self):
        # at least two low
        self.device.config.trigger_condition = 0b10
        self.device.config.one_second_enabled = True

        stew = Stew()

        logging.info("Taking data.")
        # Give hardware at least 20 seconds to startup
        t_msg = time.time() + 20
        t_log = time.time() - .5
        t_status = time.time()
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

                # Periodically send status messages to the monitor,
                # currently Nagios
                if t - t_status >= 60:
                    t_status += 60
                    self.monitor.send_uptime()
                    self.monitor.send_cpu_load()
                    self.monitor.send_trigger_rate(stew.event_rate())

        except KeyboardInterrupt:
            logging.info("Interrupted by user.")

    def store_events(self, events):
        for event in events:
            self.datastore.store_event(event)
        logging.debug("Stored %d events.", len(events))

    def write_config(self):
        self.device.config.write_config(self.config)
        with open(CONFIGFILE, 'w') as f:
            self.config.write(f)

    def close(self):
        logging.info("Writing config to file")
        self.write_config()
        self.device.close()
        self.datastore.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # raise requests module log level to WARNING
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    app = Main()
    app.run()
    app.close()
