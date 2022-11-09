import unittest

from mutwo import clock_events
from mutwo import clock_interfaces


class ClockLineTest(unittest.TestCase):
    def setUp(self):
        self.clock_line = clock_interfaces.ClockLine(clock_events.ClockEvent())

    def test_is(self):
        self.assertTrue(self.clock_line)
