# type: ignore
import unittest
from unittest import mock
from unittest.mock import call

from actions.memory import Memory
from actions.commands.get_water_level import GetWaterLevelCommand
from common.enums import State


@mock.patch('common.serial_manager.SerialManager')
@mock.patch('actions.feedback.feedback_manager.FeedbackManager')
@mock.patch('common.log_event.Logger')
@mock.patch('common.config.Config')
@mock.patch('common.redis_client.Redis')
class GetWaterLevelCommandTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()

        self.memory = Memory()
        self.noop_factory = lambda _: lambda _1, _2: None

    def test_send_serial_command(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'16', b'2'], [b'16', b'1', b'32'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)

        mock_serial.send.assert_called_once_with([16])
        mock_serial.receive.assert_called_once()

    def test_storing_pre_and_post_tank_levels(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'16', b'2'], [b'16', b'1', b'56'])
        GetWaterLevelCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'16', b'2'], [b'1', b'1', b'32'])
        GetWaterLevelCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)

        assert isinstance(self.memory.pre_weight, int)
        assert isinstance(self.memory.post_weight, int)
        assert self.memory.pre_tank_level == 56
        assert self.memory.post_tank_level == 32

    def test_storing_pre_and_post_tank_levels_multi(self, mock_serial, mock_feedback, mock_logger, mock_config,
                                                    mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'16', b'2'], [b'16', b'1', b'64'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'16', b'2'], [b'1', b'1', b'32'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'16', b'2'], [b'1', b'1', b'21'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)

        assert isinstance(self.memory.pre_weight, int)
        assert isinstance(self.memory.post_weight, int)
        assert self.memory.pre_tank_level == 32
        assert self.memory.post_tank_level == 21

    def test_adding_info_to_log_event(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'16', b'2'], [b'1', b'1', b'32'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_logger.add_to_event.assert_called_with(pre_tank_level=0, post_tank_level=32)

        mock_serial.receive.return_value = ([b'16', b'2'], [b'16', b'1', b'21'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_logger.add_to_event.assert_called_with(pre_tank_level=32, post_tank_level=21)

    def test_changing_states(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True

        mock_serial.receive.return_value = ([b'16', b'2'], [b'16', b'1', b'26'])
        GetWaterLevelCommand.run({}, {'val': [16]}, self.noop_factory, mock_feedback, self.memory, mock_redis,
                                 mock_serial, mock_config, mock_logger)
        mock_redis.update_state.assert_has_calls([call(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION),
                                                  call(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)],
                                                 any_order=False)
