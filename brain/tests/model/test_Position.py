import json
import random
import unittest

from model.position import Position


class PositionTest(unittest.TestCase):
    def test_given_a_position_then_it_is_serializable(self):
        x = random.randint(1, 100)
        y = random.randint(1, 100)
        z = random.randint(1, 100)
        expected_json = {
            "x": x,
            "y": y,
            "z": z,
        }

        position = Position(x, y, z)

        self.assertEqual(expected_json, json.loads(position.toJSON()))
