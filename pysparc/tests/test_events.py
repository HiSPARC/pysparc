import unittest

from pysparc import events


class TestMixer(unittest.TestCase):
    def setUp(self):
        self.mixer = events.Mixer()

    def test_dont_crash_when_no_master_events_yet(self):
        self.mixer._slave_events = {1234567890: 'event'}
        self.mixer._master_events = {}

        self.mixer.mix()


if __name__ == '__main__':
    unittest.main()
