import json
import random
import unittest

from model.firmware_error import FirmwareError, ErrorType


class FirmwareErrorTest(unittest.TestCase):
    def test_given_a_firmware_error_then_it_is_serializable(self):
        number = random.randint(400, 699)
        task = 'test_task'
        description = 'test_description'

        firmware_error = FirmwareError(number, task, description)

        self.assertEqual(firmware_error, FirmwareError.fromJson(firmware_error.toJson()))
