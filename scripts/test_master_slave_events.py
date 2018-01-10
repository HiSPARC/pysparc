import os.path
import logging

import tables

from pysparc.hardware import HiSPARCIII
import pysparc.align_adcs
from pysparc.messages import MeasuredDataMessage
from pysparc.storage import TablesDataStore, HisparcEvent
from pysparc.events import Event


DATAFILE = os.path.expanduser('~/data.h5')


class MasterSlaveTablesDataStore(TablesDataStore):
    def __init__(self, path, group=None):
        self.data = tables.open_file(path, 'a')
        if not group:
            group = self._get_new_sequential_group()
        self._create_group_and_tables(group)

        self.master = self.group.master
        self.slave = self.group.slave
        self.blobs = self.group.blobs

    def _create_group_and_tables(self, group):
        self.group = self.data.create_group('/', group)
        self.data.create_table(self.group, 'master', HisparcEvent)
        self.data.create_table(self.group, 'slave', HisparcEvent)
        self.data.create_vlarray(self.group, 'blobs', tables.VLStringAtom())


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    master = HiSPARCIII()
    slave = HiSPARCIII(slave=True)

    align_adcs = pysparc.align_adcs.AlignADCsMasterSlave(master, slave)
    align_adcs.align()

    master.config.ch1_voltage = 600
    master.config.ch2_voltage = 600

    master.config.ch1_threshold_low = 250
    master.config.ch1_threshold_high = 320
    master.config.ch2_threshold_low = 250
    master.config.ch2_threshold_high = 320

    master.config.trigger_condition = master.config.build_trigger_condition(
        num_high=1)

    datastore = MasterSlaveTablesDataStore(DATAFILE)

    while True:
        for dev, table in zip([master, slave], ['master', 'slave']):
            msg = dev.read_message()
            if type(msg) == MeasuredDataMessage:
                datastore.store_event(Event(msg), table)
