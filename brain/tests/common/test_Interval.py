# type: ignore
import random
import unittest
from typing import Any
from unittest.mock import MagicMock, patch
import time

from common.Interval import Interval


class FakePeriodHandler:

    def periodic_method(self, arg1, arg2):
        return 'not important' + arg1 + arg2


def fake_arguments_generator() -> tuple[Any, ...]:
    return ("arg1: " + str(random.choice([0, 1, 2, 3])), "arg2: " + str(random.choice([0, 1, 2, 3])))


class IntervalTest(unittest.TestCase):
    @patch('random.choice')
    def test_given_an_action_when_it_is_delayed_of_x_seconds_then_it_will_be_executed_only_when_deadline_is_reached(
            self, mock_random):
        fake_periodic_handler = FakePeriodHandler()
        fake_periodic_handler.periodic_method = MagicMock()
        mock_random.side_effect = [0, 1, 2, 3]

        interval = Interval(5, fake_periodic_handler.periodic_method, fake_arguments_generator)
        try:
            self.assertEqual(0, fake_periodic_handler.periodic_method.call_count)

            time.sleep(3)
            self.assertEqual(0, fake_periodic_handler.periodic_method.call_count)

            time.sleep(2.5)
            self.assertEqual(fake_periodic_handler.periodic_method.call_count, 1)
            self.assertEqual("arg1: 0", fake_periodic_handler.periodic_method.call_args.args[0])
            self.assertEqual("arg2: 1", fake_periodic_handler.periodic_method.call_args.args[1])

            time.sleep(3)
            interval.reset()
            time.sleep(2.5)
            self.assertEqual(fake_periodic_handler.periodic_method.call_count, 1)

            time.sleep(5)
            self.assertEqual(fake_periodic_handler.periodic_method.call_count, 2)
            self.assertEqual("arg1: 2", fake_periodic_handler.periodic_method.call_args.args[0])
            self.assertEqual("arg2: 3", fake_periodic_handler.periodic_method.call_args.args[1])
        finally:
            interval.stop()
