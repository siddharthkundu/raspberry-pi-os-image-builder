# type: ignore
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

from common.log_event import Logger


@mock.patch('common.config.Config')
@mock.patch('logging.FileHandler')
class LogTest(unittest.TestCase):

    @staticmethod
    def test_given_a_logger_when_create_an_event_then_zulu_format_is_used(self, mock_config, mock_file_handler):
        mock_config.log_level_file = "DEBUG"
        mock_config.log_level_terminal = "DEBUG"
        logger = Logger(mock_config)
        logger._get_utc_now = MagicMock()
        logger._get_utc_now.return_value = datetime(2021, 12, 14, 9, 45, 24, 132221)
        expected_instructionStartTime = "2021-12-14T09:45:24.132Z"

        logger.create_event("fake message")

        self.assertEqual(logger._log_event.get_state()["startTime"], expected_instructionStartTime)

    @staticmethod
    def test_given_a_logger_when_send_an_event_then_zulu_format_is_used(self, mock_config, mock_file_handler):
        mock_config.log_level_file = "DEBUG"
        mock_config.log_level_terminal = "DEBUG"
        logger = Logger(mock_config)
        logger._get_utc_now = MagicMock()
        logger._get_utc_now.return_value = datetime(2021, 12, 14, 9, 45, 24, 132221)
        expected_instructionEndTime = "2021-12-14T09:45:24.132Z"

        logger.create_event("fake message")
        logger.send_event(1)

        self.assertEqual(logger._log_event.get_state()["endTime"], expected_instructionEndTime)
