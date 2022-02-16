# type: ignore
import unittest
from unittest import mock
from unittest.mock import call

from actions.memory import Memory
from common.enums import State
from actions.commands.weight import WeightCommand


@mock.patch('common.serial_manager.SerialManager')
@mock.patch('actions.feedback.feedback_manager.FeedbackManager')
@mock.patch('common.log_event.Logger')
@mock.patch('common.config.Config')
@mock.patch('common.redis_client.Redis')
class WeightCommandTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()

        self.memory = Memory()
        self.noop_factory = lambda _: lambda _1, _2: None

    def test_send_serial_command(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        mock_serial.send.assert_called_once_with([1])
        mock_serial.receive.assert_called_once()

    def test_calculate_weight_wo_offset(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        assert isinstance(self.memory.post_weight, int)
        assert self.memory.post_weight == 1100

    def test_calculate_weight_with_negative_offset(self, mock_serial, mock_feedback, mock_logger, mock_config,
                                                   mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = -300

        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        assert isinstance(self.memory.post_weight, int)
        assert self.memory.post_weight == 800

    def test_calculate_weight_with_positive_offset(self, mock_serial, mock_feedback, mock_logger, mock_config,
                                                   mock_redis):
        mock_serial.send.return_value = True
        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 400

        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        assert isinstance(self.memory.post_weight, int)
        assert self.memory.pre_weight == 0
        assert self.memory.post_weight == 1500

    def test_storing_pre_and_post_weight(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'1', b'1', b'700'], [b'1', b'1', b'950'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        assert isinstance(self.memory.pre_weight, int)
        assert isinstance(self.memory.post_weight, int)
        assert self.memory.pre_weight == 1100
        assert self.memory.post_weight == 1650

    def test_storing_pre_and_post_weight_multi(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'1', b'1', b'700'], [b'1', b'1', b'950'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_serial.receive.return_value = ([b'1', b'1', b'150'], [b'1', b'1', b'200'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)

        assert isinstance(self.memory.pre_weight, int)
        assert isinstance(self.memory.post_weight, int)
        assert self.memory.pre_weight == 1650
        assert self.memory.post_weight == 350

    def test_adding_info_to_log_event(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_logger.add_to_event.assert_called_with(pre_weight=0, post_weight=1100)

        mock_serial.receive.return_value = ([b'1', b'1', b'700'], [b'1', b'1', b'950'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_logger.add_to_event.assert_called_with(pre_weight=1100, post_weight=1650)

    def test_changing_states(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_redis.update_state.assert_has_calls([
            call(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION),
            call(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        ], any_order=False)

    def test_sending_response(self, mock_serial, mock_feedback, mock_logger, mock_config, mock_redis):
        mock_serial.send.return_value = True
        mock_serial.is_ok.return_value = True
        mock_logger.add_to_event.return_value = True
        mock_redis.update_state.return_value = True
        mock_config.weight_offset = 0

        mock_serial.receive.return_value = ([b'1', b'1', b'500'], [b'1', b'1', b'600'])
        WeightCommand.run({}, {'val': [1]}, self.noop_factory, mock_feedback, self.memory, mock_redis, mock_serial,
                          mock_config, mock_logger)
        mock_redis.update_state.assert_has_calls([
            call(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION),
            call(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        ], any_order=False)
