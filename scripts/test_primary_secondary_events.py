import os.path
import logging

import tables

from pysparc.hardware import HiSPARCIII
import pysparc.align_adcs
from pysparc.messages import MeasuredDataMessage
from pysparc.storage import TablesDataStore, HisparcEvent
from pysparc.events import Event


DATAFILE = os.path.expanduser('~/data.h5')


class PrimarySecondaryTablesDataStore(TablesDataStore):
    def __init__(self, path, group=None):
        self.data = tables.open_file(path, 'a')
        if not group:
            group = self._get_new_sequential_group()
        self._create_group_and_tables(group)

        self.primary = self.group.primary
        self.secondary = self.group.secondary
        self.blobs = self.group.blobs

    def _create_group_and_tables(self, group):
        self.group = self.data.create_group('/', group)
        self.data.create_table(self.group, 'primary', HisparcEvent)
        self.data.create_table(self.group, 'secondary', HisparcEvent)
        self.data.create_vlarray(self.group, 'blobs', tables.VLStringAtom())


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    primary = HiSPARCIII()
    secondary = HiSPARCIII(secondary=True)

    align_adcs = pysparc.align_adcs.AlignADCsPrimarySecondary(primary, secondary)
    align_adcs.align()

    primary.config.ch1_voltage = 600
    primary.config.ch2_voltage = 600

    primary.config.ch1_threshold_low = 250
    primary.config.ch1_threshold_high = 320
    primary.config.ch2_threshold_low = 250
    primary.config.ch2_threshold_high = 320

    primary.config.pre_coincidence_time = 2.0
    primary.config.coincidence_time = 3.0
    primary.config.post_coincidence_time = 4.0

    primary.config.trigger_condition = primary.config.build_trigger_condition(
        num_high=1)

    datastore = PrimarySecondaryTablesDataStore(DATAFILE)

    while True:
        for dev, table in zip([primary, secondary], ['primary', 'secondary']):
            msg = dev.read_message()
            if type(msg) == MeasuredDataMessage:
                datastore.store_event(Event(msg), table)
