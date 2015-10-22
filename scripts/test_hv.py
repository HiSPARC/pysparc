import datetime
import logging
import os
import time
import ConfigParser

import pkg_resources

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS
from pysparc.ftdi_chip import DeviceNotFoundError
from pysparc.align_adcs import AlignADCs
from pysparc.events import Stew, ConfigEvent
from pysparc import messages, storage, monitor


SYSTEM_CONFIGFILE = pkg_resources.resource_filename('pysparc', 'config.ini')
CONFIGFILE = os.path.expanduser('~/.pysparc')
ALL_CONFIG_FILES = [SYSTEM_CONFIGFILE, CONFIGFILE]
DATAFILE = 'hisparc.h5'


class Main(object):

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        try:
            self.device = HiSPARCIII()
        except DeviceNotFoundError:
            self.device = HiSPARCII()
        self.gps = TrimbleGPS()
        self.initialize_device()

        station_name = self.config.get('DAQ', 'station_name')
        station_number = self.config.getint('DAQ', 'station_number')
        station_password = self.config.get('DAQ', 'station_password')

        # self.datastore1 = storage.TablesDataStore(DATAFILE)
        self.datastore2 = storage.NikhefDataStore(station_number,
                                                  station_password)
        self.storage_manager = storage.StorageManager()
        # self.storage_manager.add_datastore(self.datastore1, 'queue_file')
        self.storage_manager.add_datastore(self.datastore2, 'queue_nikhef')
        self.monitor = monitor.Monitor(station_name)

    def initialize_device(self):
        logging.info("Reading config from file")
        self.config.read(ALL_CONFIG_FILES)

        logging.info("Initializing device configuration")
        self.device.config.read_config(self.config)

        if self.config.getboolean('DAQ', 'force_reset_gps'):
            logging.info("Force reset GPS to factory defaults.")
            self.gps.reset_defaults()
            self.config.set('DAQ', 'force_reset_gps', False)

        if self.config.getboolean('DAQ', 'force_align_adcs'):
            logging.info("Force aligning ADCs.")
            align_adcs = AlignADCs(self.device)
            align_adcs.align()
            self.config.set('DAQ', 'force_align_adcs', False)

        self.write_config()

    def run(self):
        # The first configuration message does not include GPS information.
        # Flush it, and possibly other outdated messages, and request it later.
        self.device.flush_device()

        stew = Stew()

        logging.info("Taking data.")
        # Give hardware at least 20 seconds to startup
        t_msg = time.time() + 20
        t_log = time.time() - .5
        t_status = time.time()
        t_config = datetime.date(1970, 1, 1)
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
                        logging.debug("One-second received: %d", msg.timestamp)
                    elif isinstance(msg, messages.ControlParameterList):
                        config = ConfigEvent(self.device.config)
                        self.storage_manager.store_event(config)
                        t_config = datetime.date.today()
                        logging.info("Sent configuration message.")
                else:
                    if t - t_msg > 20:
                        logging.warning("Hardware is silent, resetting.")
                        self.device.reset_hardware()
                        # Give hardware at least 20 seconds to startup
                        t_msg = t

                if t - t_log >= 1:
                    logging.info("Event rate: %.1f Hz", stew.event_rate())
                    t_log += 1

                    stew.stir()
                    events = stew.serve_events()
                    self.store_events(events)
                    stew.drain()

                # Periodically send status messages to the monitor,
                # currently Nagios, and config messages
                if t - t_status >= 60:
                    t_status += 60
                    self.monitor.send_uptime()
                    self.monitor.send_cpu_load()
                    self.monitor.send_trigger_rate(stew.event_rate())
                    if t_config < datetime.date.today():
                        # update config (set t_config when sent, not here)
                        self.device.send_message(
                            messages.GetControlParameterList())

        except KeyboardInterrupt:
            logging.info("Interrupted by user.")

    def store_events(self, events):
        for event in events:
            try:
                self.storage_manager.store_event(event)
            except Exception as e:
                logging.error(str(e))
        logging.debug("Stored %d events.", len(events))

    def write_config(self):
        self.device.config.write_config(self.config)
        with open(CONFIGFILE, 'w') as f:
            self.config.write(f)

    def close(self):
        logging.info("Closing down")
        self.device.close()
        self.storage_manager.close()
        # self.datastore1.close()
        self.datastore2.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
    # raise requests module log level to WARNING
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.WARNING)

    app = Main()
    try:
        app.run()
    finally:
        app.close()
