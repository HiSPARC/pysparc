"""Test the StorageManager and StorageWorkers

Create fake datastores and fake events, and send them off to the
StorageManager.

"""


import random
import time
import logging

from pysparc import storage


class FakeEvent(object):

    def __init__(self):
        self.timestamp = int(time.time())
        self.nanoseconds = random.randint(0, 1000000000)
        self.ext_timestamp = self.timestamp * 1000000000 + self.nanoseconds


class FakeDataStore(storage.BaseDataStore):

    def store_event(self, event):
        if random.random() < .1:
            raise storage.StorageError("Random foo exception!")


def main():
    datastore1 = FakeDataStore()

    manager = storage.StorageManager()
    manager.add_datastore(datastore1, 'queue1')

    while True:
        if random.random() < .5:
            print "Event created."
            manager.store_event(FakeEvent())
        if random.random() < .6:
            for queue, worker in manager.workers:
                print queue, "Store event."
                worker.store_event()
        time.sleep(.5)


if __name__ == '__main__':
    logging.basicConfig()
    main()
