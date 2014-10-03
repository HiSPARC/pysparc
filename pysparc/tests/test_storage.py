import unittest
import cPickle as pickle
import threading

from mock import Mock, patch, sentinel, call

from pysparc import storage


class StorageManagerTest(unittest.TestCase):

    def setUp(self):
        patcher = patch('redis.StrictRedis')
        self.addCleanup(patcher.stop)
        mock_KVStore = patcher.start()
        self.mock_kvstore = mock_KVStore.return_value

        self.manager = storage.StorageManager()

    def test_workers_attribute(self):
        self.assertIs(type(self.manager.workers), list)

    def test_kvstore_attribute(self):
        self.assertIs(self.manager.kvstore, self.mock_kvstore)

    @patch('pysparc.storage.StorageWorker')
    def test_add_datastore(self, mock_Worker):
        mock_worker = mock_Worker.return_value
        mock_datastore = Mock()

        self.manager.add_datastore(mock_datastore, sentinel.queue)

        self.assertIn((sentinel.queue, mock_worker), self.manager.workers)


class StorageManagerStoreEventTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('redis.StrictRedis')
        patcher2 = patch('cPickle.dumps')
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        mock_KVStore = patcher1.start()
        self.mock_kvstore = mock_KVStore.return_value
        self.mock_pickle_dumps = patcher2.start()

        self.manager = storage.StorageManager()

    def test_store_event_adds_event_to_kvstore(self):
        event = Mock(name='event')
        event.ext_timestamp = 1234567890
        key = 'event_1234567890'
        self.mock_pickle_dumps.return_value = sentinel.pickled_event

        self.manager.store_event(event)

        self.mock_pickle_dumps.assert_called_once_with(event)
        self.mock_kvstore.hmset.assert_called_once_with(
            key, {'event': sentinel.pickled_event, 'count': 0})

    def test_store_event_adds_event_key_to_queues(self):
        event = Mock(name='event')
        event.ext_timestamp = 1234567890
        key = 'event_1234567890'
        self.manager.workers = [(sentinel.queue1, sentinel.worker1),
                                (sentinel.queue2, sentinel.worker2)]

        self.manager.store_event(event)

        expected = [call(sentinel.queue1, key), call(sentinel.queue2, key)]
        self.assertEqual(self.mock_kvstore.rpush.call_args_list, expected)

    def test_store_event_increments_counter(self):
        # add 5 tuples as workers
        self.manager.workers = 5 * [(0, 0)]
        event = Mock(name='event')
        event.ext_timestamp = 1234567890
        key = 'event_1234567890'

        self.manager.store_event(event)

        expected = 5 * [call(key, 'count', 1)]
        self.assertEqual(self.mock_kvstore.hincrby.call_args_list, expected)


class StorageWorkerStoreEventTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch.object(storage.StorageWorker, 'get_key_from_queue')
        patcher2 = patch.object(storage.StorageWorker, 'store_event_by_key')
        patcher3 = patch('time.sleep')
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)
        self.mock_get_key_from_queue = patcher1.start()
        self.mock_store_event_by_key = patcher2.start()
        self.mock_sleep = patcher3.start()

        self.worker = storage.StorageWorker(Mock(), Mock(), Mock())

    def test_store_event_or_sleep_calls_get_key_from_queue(self):
        self.worker.store_event_or_sleep()
        self.mock_get_key_from_queue.assert_called_once_with()

    def test_store_event_or_sleep_calls_store_event_by_key_if_key_and_doesnt_sleep(self):
        self.mock_get_key_from_queue.return_value = sentinel.key

        self.worker.store_event_or_sleep()

        self.mock_store_event_by_key.assert_called_once_with(sentinel.key)
        self.assertFalse(self.mock_sleep.called)

    def test_store_event_or_sleep_sleeps_if_not_key_and_doesnt_store(self):
        self.mock_get_key_from_queue.return_value = None

        self.worker.store_event_or_sleep()

        self.assertFalse(self.mock_store_event_by_key.called)
        self.mock_sleep.assert_called_once_with(storage.SLEEP_INTERVAL)

    def test_store_event_calls_get_key_from_queue(self):
        self.worker.store_event()
        self.mock_get_key_from_queue.assert_called_once_with()

    def test_store_event_calls_store_event_by_key_if_key_and_doesnt_sleep(self):
        self.mock_get_key_from_queue.return_value = sentinel.key

        self.worker.store_event()

        self.mock_store_event_by_key.assert_called_once_with(sentinel.key)
        self.assertFalse(self.mock_sleep.called)


class StorageWorkerStoreEventByKeyTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch.object(storage.StorageWorker, 'remove_event_from_queue')
        patcher2 = patch.object(storage.StorageWorker, 'get_event_by_key')
        patcher3 = patch.object(storage, 'logger')
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(patcher3.stop)

        self.mock_remove_event = patcher1.start()
        self.mock_get_event_by_key = patcher2.start()
        self.mock_logger = patcher3.start()

        self.mock_datastore = Mock()
        self.worker = storage.StorageWorker(self.mock_datastore,
                                            Mock(), Mock())

    def test_datastore_attribute(self):
        self.assertIs(self.mock_datastore, self.worker.datastore)

    def test_store_event_by_key(self):
        self.mock_get_event_by_key.return_value = sentinel.event

        self.worker.store_event_by_key(sentinel.key)

        self.mock_get_event_by_key.assert_called_once_with(sentinel.key)
        self.mock_datastore.store_event.assert_called_once_with(sentinel.event)

    def test_store_event_by_key_catches_and_logs_StorageError_but_not_all(self):
        # Catch StorageError, and log
        exception = storage.StorageError("Foo")
        self.mock_datastore.store_event.side_effect = exception
        self.worker.store_event_by_key(sentinel.key)
        self.mock_logger.error.assert_called_once_with(str(exception))

        # Catch all exceptions, but raise new StorageError
        self.mock_datastore.store_event.side_effect = Exception()
        self.assertRaises(storage.StorageError, self.worker.store_event_by_key, sentinel.key)

    def test_store_event_by_key_calls_remove_event_only_if_no_exception(self):
        self.mock_datastore.store_event.side_effect = storage.StorageError("Foo")
        self.worker.store_event_by_key(sentinel.key)
        self.assertFalse(self.mock_remove_event.called)

        self.mock_datastore.store_event.side_effect = None
        self.worker.store_event_by_key(sentinel.key)
        self.mock_remove_event.assert_called_once_with(sentinel.key)


class StorageWorkerKVStoreTest(unittest.TestCase):

    def setUp(self):
        self.mock_kvstore = Mock()
        self.mock_queue = sentinel.queue
        self.worker = storage.StorageWorker(Mock(),
                                            self.mock_kvstore,
                                            self.mock_queue)

    def test_kvstore_attribute(self):
        self.assertIs(self.mock_kvstore, self.worker.kvstore)

    def test_queue_attribute(self):
        self.assertIs(self.mock_queue, self.worker.queue)

    def test_remove_event_from_queue_removes_from_queue_and_decr_counter(self):
        self.mock_kvstore.lpop.return_value = sentinel.key

        self.worker.remove_event_from_queue(sentinel.key)

        # remove first element from queue
        self.mock_kvstore.lpop.assert_called_once_with(self.mock_queue)
        # decrease event counter
        self.mock_kvstore.hincrby.assert_called_once_with(sentinel.key, 'count', -1)

    def test_remove_event_from_queue_removes_event_only_if_counter_zero(self):
        self.mock_kvstore.lpop.return_value = sentinel.key

        self.mock_kvstore.hincrby.return_value = 1
        self.worker.remove_event_from_queue(sentinel.key)
        self.assertFalse(self.mock_kvstore.delete.called)

        self.mock_kvstore.hincrby.return_value = 0
        self.worker.remove_event_from_queue(sentinel.key)
        self.mock_kvstore.delete.assert_called_once_with(sentinel.key)

    def test_remove_event_from_queue_raises_IntegrityError(self):
        self.mock_kvstore.lpop.return_value = sentinel.other_key

        self.assertRaises(storage.IntegrityError, self.worker.remove_event_from_queue, sentinel.key)

    def test_get_key_from_queue(self):
        self.mock_kvstore.lindex.return_value = sentinel.key

        key = self.worker.get_key_from_queue()

        # get first event key from queue
        self.mock_kvstore.lindex.assert_called_once_with(self.mock_queue, 0)
        self.assertIs(key, sentinel.key)

    @patch('cPickle.loads')
    def test_get_event_by_key(self, mock_pickle_loads):
        pickled_event = sentinel.pickled_event
        self.mock_kvstore.hget.return_value = pickled_event
        mock_pickle_loads.return_value = sentinel.event

        event = self.worker.get_event_by_key(sentinel.key)

        # get 'event' from event key (is pickled event)
        self.mock_kvstore.hget.assert_called_once_with(sentinel.key, 'event')
        # unpickle event
        mock_pickle_loads.assert_called_once_with(pickled_event)
        # check return values
        self.assertIs(event, sentinel.event)


class StorageWorkerThreadingTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch.object(storage.StorageWorker, 'store_event_or_sleep')
        self.addCleanup(patcher1.stop)
        self.mock_store = patcher1.start()
        self.mock_store.side_effect = [None]
        self.mock_signal = Mock()
        self.mock_signal.is_set.return_value = False

        self.worker = storage.StorageWorker(Mock(), Mock(), Mock(),
                                            self.mock_signal)

    def test_StorageWorker_subclasses_Thread(self):
        self.assertIsInstance(self.worker, threading.Thread)

    def test_StorageWorker_shutdown_signal_attribute(self):
        self.assertIs(self.worker._must_shutdown, self.mock_signal)

    def test_run_calls_store_event_or_sleep_in_loop(self):
        N = 10
        self.mock_store.side_effect = N * [None]

        # a StopIteration means the test finished 10 succesfull calls
        self.assertRaises(StopIteration, self.worker.run)

        # check correct call, and call count
        self.mock_store.assert_called_with()
        self.assertEqual(self.mock_store.call_count, N + 1)

    def test_run_returns_if_shutdown_signal_is_set(self):
        self.mock_signal.is_set.return_value = True
        try:
            self.worker.run()
        except StopIteration:
            self.fail('Did not shutdown')
        self.assertFalse(self.mock_store.called)

    def test_run_returns_after_shutdown_signal(self):
        self.mock_store.side_effect = self.side_effect_with_shutdown()

        try:
            self.worker.run()
        except StopIteration:
            self.fail('Did not shutdown')

    def side_effect_with_shutdown(self):
        for i in range(5):
            yield None
        self.mock_signal.is_set.return_value = True
        for i in range(5):
            yield None


if __name__ == '__main__':
    unittest.main()
