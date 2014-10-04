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

    def __init__(self):
        super(FakeDataStore, self).__init__()
        self._stored_timestamps = []

    def store_event(self, event):
        time.sleep(random.uniform(0, .5))
        if random.random() < .1:
            # Ohoh, problem!
            time.sleep(random.uniform(.5, 1))
            raise storage.StorageError("Random foo exception!")
        else:
            # Yes, succesful!
            self._stored_timestamps.append(event.ext_timestamp)


def create_event():
    if random.random() < .5:
        print "Event created."
        event = FakeEvent()
        manager.store_event(event)
        time.sleep(random.uniform(0, .2))
        return event.ext_timestamp
    else:
        return None


def main():
    global manager

    datastore1 = FakeDataStore()
    datastore2 = FakeDataStore()

    manager = storage.StorageManager()
    manager.add_datastore(datastore1, 'queue1')
    manager.add_datastore(datastore2, 'queue2')

    created_timestamps = []

    t0 = time.time()
    while time.time() - t0 < 2:
        ts = create_event()
        if ts:
            created_timestamps.append(ts)

    t0 = time.time()
    print "Storing backlog!!!"
    time.sleep(10)
    
    st1 = datastore1._stored_timestamps
    st2 = datastore2._stored_timestamps
    print len(set(st1)), len(set(st2)), set(st1) == set(st2)
    print len(st1), len(st2), st1 == st2

    assert st1 == st2 == created_timestamps


if __name__ == '__main__':
    logging.basicConfig()

    try:
        main()
    except:
        raise
    finally:
        manager.close()
