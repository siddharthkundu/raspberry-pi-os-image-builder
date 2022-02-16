import random
import unittest
from unittest import mock
from unittest.mock import patch

import serial

from common.serial_manager import SerialManager
from model.firmware_error import FirmwareError


@mock.patch('common.config.Config')
@mock.patch('common.log_event.Logger')
@mock.patch('actions.feedback.firmware_error_info.FirmwareErrorInfo')
@mock.patch('glob.glob')
@mock.patch('serial.Serial.__init__', mock.Mock(return_value=None))
class TestSerialManager(unittest.TestCase):

    def test_given_a_error_in_serial_output_when_is_ok_is_called_then_false_is_returned(self, mock_glob, mock_firmware_error_info, mock_logger, mock_config):  # noqa: E501
        mock_glob.return_value = ['/dev/tty1', '/dev/tty2']

        with (patch.object(serial.Serial, "write", return_value=None),
              patch.object(serial.Serial, "readline", return_value=b'')):

            serial_manager = SerialManager(mock_config, mock_logger, mock_firmware_error_info)
            self.assertFalse(serial_manager.is_ok([b'5', b'1', b'50020'], [b'5', b'2', b'50023']))
            self.assertFalse(serial_manager.is_ok([b'4', b'1', b'50020'], [b'5', b'2', b'50023']))
            self.assertFalse(serial_manager.is_ok([b'5', b'1', b'50020'], [b'4', b'2', b'50023']))
            self.assertTrue(serial_manager.is_ok([b'4', b'1', b'50020'], [b'4', b'2', b'50023']))

    def test_given_a_error_in_serial_output_when_get_error_info_is_called_then_a_proper_error_is_returned(self, mock_glob, mock_firmware_error_info, mock_logger, mock_config):  # noqa: E501
        mock_glob.return_value = ['/dev/tty1', '/dev/tty2']

        with (patch.object(serial.Serial, "write", return_value=None),
              patch.object(serial.Serial, "readline", return_value=b'')):
            expected_firmware_errors = [FirmwareError(random.randint(5000, 6000), 'Fake error 1', 'Fake error 1'),
                                        FirmwareError(random.randint(5000, 6000), 'Fake error 2', 'Fake error 2')]

            mock_firmware_error_info.get_error.side_effect = expected_firmware_errors

            serial_manager = SerialManager(mock_config, mock_logger, mock_firmware_error_info)
            actual_firmware_errors = serial_manager.get_firmware_error([b'5', b'1', b'50020'], [b'5', b'2', b'50023'])
            self.assertEqual(expected_firmware_errors, actual_firmware_errors)

    def test_given_no_errors_in_serial_output_when_get_error_info_is_called_then_an_empty_list_is_returned(self, mock_glob, mock_firmware_error_info, mock_logger, mock_config):  # noqa: E501
        mock_glob.return_value = ['/dev/tty1', '/dev/tty2']

        with (patch.object(serial.Serial, "write", return_value=None),
              patch.object(serial.Serial, "readline", return_value=b'')):
            expected_firmware_errors = []

            mock_firmware_error_info.get_error.side_effect = expected_firmware_errors

            serial_manager = SerialManager(mock_config, mock_logger, mock_firmware_error_info)
            actual_firmware_errors = serial_manager.get_firmware_error([b'4', b'1', b'50020'], [b'3', b'2', b'50023'])
            self.assertEqual(expected_firmware_errors, actual_firmware_errors)
