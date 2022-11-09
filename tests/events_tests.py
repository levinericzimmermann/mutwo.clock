import unittest

from mutwo import clock_events


class ClockEventTest(unittest.TestCase):
    def _test_tag(self):
        self.assertEqual(
            clock_events.ClockEvent().tag, clock_events.configurations.DEFAULT_CLOCK_TAG
        )

    def test_tag(self):
        self._test_tag()
        clock_events.configurations.DEFAULT_CLOCK_TAG = "my-clock"
        self._test_tag()
