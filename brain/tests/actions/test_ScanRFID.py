# type: ignore
import unittest
import random
from unittest import mock
from unittest.mock import call

from actions.memory import Memory
from actions.commands.scan_rfid import ScanRFIDCommand
from common.enums import State
from model.firmware_error import FirmwareError


@mock.patch('common.serial_manager.SerialManager')
@mock.patch('actions.feedback.feedback_manager.FeedbackManager')
@mock.patch('common.log_event.Logger')
@mock.patch('common.config.Config')
@mock.patch('common.redis_client.Redis')
class ScanRFIDTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.memory = Memory()
        self.noop_factory = lambda _: lambda _1, _2: None

    def test_send_serial_command(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.01.02'], [b'6', b'1', b'0'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        ScanRFIDCommand.run({'type': 'WATER'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)

        mock_serial.send.assert_called_once_with([6])
        mock_serial.receive.assert_called_once()

    def test_memory_update(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.01.02.03.04'], [b'6', b'1', b'0'])
        ScanRFIDCommand.run({'type': 'WATER'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)
        assert self.memory.current_rfid == 'te.st.01.02.03.04'

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.05.06'], [b'6', b'1', b'0'])
        ScanRFIDCommand.run({'type': 'ONBOARD'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)
        assert self.memory.current_rfid == 'te.st.05.06'

    def test_adding_info_to_log_event(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.01.02.03'], [b'6', b'1', b'0'])
        ScanRFIDCommand.run({'type': 'WATER'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)
        mock_logger.add_to_event.assert_called_with(rfid='te.st.01.02.03')

    def test_changing_states(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.01.02.03.04'], [b'6', b'1', b'0'])
        ScanRFIDCommand.run({'type': 'ONBOARD'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)
        mock_redis.update_state.assert_has_calls([call(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION),
                                                  call(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)],
                                                 any_order=False)

    def test_onboard_failure_when_rfids_do_not_match(self, mock_serial, mock_feedback, mock_logger, mock_config,
                                                     mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.07.08'], [b'6', b'1', b'0'])
        firmware_errors = [FirmwareError(random.randint(5000, 6000), 'Fake error 1', 'Fake error 1'),
                           FirmwareError(random.randint(5000, 6000), 'Fake error 2', 'Fake error 2')]
        mock_serial.get_firmware_error.return_value = firmware_errors
        firmware_errors_json = [firmware_error.toJson() for firmware_error in firmware_errors]
        test_instruction = {'type': 'ONBOARD', 'gutterId': 'te.st.07'}

        ScanRFIDCommand.run(test_instruction, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)

        details = {'statusCode': 'RFID != gutter_id',
                   'message': "ONBOARD failed: expected- te.st.07, received- te.st.07.08"}
        mock_logger.add_to_event.assert_called_once_with(statusCode=details['statusCode'],
                                                         error_message=details['message'],
                                                         firmware_errors=firmware_errors_json)

    def test_onboard_failure_when_no_gutterid_in_instruction(self, mock_serial, mock_feedback, mock_logger,
                                                             mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'te.st.07.08'], [b'6', b'1', b'0'])
        firmware_errors = [FirmwareError(random.randint(5000, 6000), 'Fake error 1', 'Fake error 1'),
                           FirmwareError(random.randint(5000, 6000), 'Fake error 2', 'Fake error 2')]
        mock_serial.get_firmware_error.return_value = firmware_errors
        firmware_errors_json = [firmware_error.toJson() for firmware_error in firmware_errors]
        ScanRFIDCommand.run({'type': 'ONBOARD'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)

        details = {'statusCode': 'HorizontalBotRFIDReadError',
                   'message': "Received ONBOARD instruction without gutterId."}
        mock_logger.add_to_event.assert_called_once_with(statusCode=details['statusCode'],
                                                         error_message=details['message'],
                                                         firmware_errors=firmware_errors_json)

    def test_onboard_failure_when_no_rfid_in_serial_response(self, mock_serial, mock_feedback, mock_logger,
                                                             mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'0'], [b'6', b'1', b'0'])
        firmware_errors = [FirmwareError(random.randint(5000, 6000), 'Fake error 1', 'Fake error 1'),
                           FirmwareError(random.randint(5000, 6000), 'Fake error 2', 'Fake error 2')]
        mock_serial.get_firmware_error.return_value = firmware_errors
        firmware_errors_json = [firmware_error.toJson() for firmware_error in firmware_errors]
        ScanRFIDCommand.run({'type': 'ONBOARD'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)

        details = {'statusCode': 'HorizontalBotRFIDReadError',
                   'message': 'ONBOARD failed because of no RFID'}
        mock_logger.add_to_event.assert_called_with(
            statusCode=details['statusCode'],
            error_message=details['message'],
            firmware_errors=firmware_errors_json)

    def test_scan_to_onboard_failure_when_no_rfid_in_serial_response(self, mock_serial, mock_feedback, mock_logger,
                                                                     mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'6', b'2', b'0'], [b'6', b'1', b'0'])
        firmware_errors = [FirmwareError(random.randint(5000, 6000), 'Fake error 1', 'Fake error 1'),
                           FirmwareError(random.randint(5000, 6000), 'Fake error 2', 'Fake error 2')]
        mock_serial.get_firmware_error.return_value = firmware_errors
        firmware_errors_json = [firmware_error.toJson() for firmware_error in firmware_errors]
        ScanRFIDCommand.run({'type': 'SCAN_TO_ONBOARD'}, {'val': [6]}, self.noop_factory, mock_feedback, self.memory,
                            mock_redis, mock_serial, mock_config, mock_logger)

        details = {'statusCode': 'HorizontalBotRFIDReadError',
                   'message': 'SCAN_TO_ONBOARD failed because of no RFID'}
        mock_logger.add_to_event.assert_called_once_with(statusCode=details['statusCode'],
                                                         error_message=details['message'],
                                                         firmware_errors=firmware_errors_json)
