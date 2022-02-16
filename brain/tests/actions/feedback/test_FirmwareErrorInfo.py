import unittest

from actions.feedback.firmware_error_info import FirmwareErrorInfo
from model.firmware_error import FirmwareError, ErrorType


class FirmwareErrorInfoTest(unittest.TestCase):
    def setUp(self):
        self.firmwareErrorInfo = FirmwareErrorInfo('./test_error_codes.txt')

    def test_given_a_valid_error_code_then_it_is_fetched(self):
        expected_firmware_error = FirmwareError(
            50711,
            'home',
            'X movement not executed, because double movement is set.')

        actual_firmware_error = self.firmwareErrorInfo.get_error(50711)

        self.assertEqual(expected_firmware_error, actual_firmware_error)
        self.assertEqual(ErrorType.WARNING, actual_firmware_error.error_type)

    def test_given_a_invalid_error_code_then_it_is_returned_as_None(self):
        expected_firmware_error = None

        actual_firmware_error = self.firmwareErrorInfo.get_error(50911)

        self.assertEqual(expected_firmware_error, actual_firmware_error)
