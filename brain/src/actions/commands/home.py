from typing import List
import logging

from common.enums import State, ErrorHandlerCode, CommandSemantics
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager
from actions.commands.get_position import GetPositionCommand


class HomeCommand:
    @staticmethod
    def run(instruction: Instruction,
            action: Command,
            error_handler_factory: ErrorHandlerFactoryFunc,
            feedback_manager: FeedbackManager,
            memory: Memory,
            redis: Redis,
            serial: SerialManager,
            config: Config,
            logger: Logger,
            fatal: bool = False,
            fatal_recovery: bool = False) -> bool:

        if fatal_recovery:
            error_handler = error_handler_factory(ErrorHandlerCode.FATAL_RECOVERY_HOMING)
        elif fatal:
            error_handler = error_handler_factory(ErrorHandlerCode.FATAL_HOMING)
        else:
            error_handler = error_handler_factory(ErrorHandlerCode.STANDARD)

        command: List[int] = [int(x) for x in action['val']]
        if command[CommandSemantics.HOMING_X_POS.value] == 1:
            state = State.HOMING_X
        elif command[CommandSemantics.HOMING_Y_POS.value] == 1:
            state = State.HOMING_Y
        else:
            state = State.HOMING_Z
        redis.update_state(State.add_state_remove_IDLE, state)

        serial.send(command)
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotHomingError',
                'message': 'Horizontal Robot failed while homing'
            }
            logger.add_to_event(
                statusCode=details['statusCode'],
                error_message=details['message'],
                firmware_errors=[
                    error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)
                ])
            error_handler(instruction, action)
            redis.update_state(State.remove_state_add_IDLE, state)

            logger.log_system(logging.ERROR, details['message'])
            logger.send_event(logging.ERROR)
            feedback_manager.send_to_gateway(instruction, action, memory, details)
            return False

        if not GetPositionCommand.run(instruction, {'val': ['9']}, error_handler_factory, feedback_manager, memory,
                                      redis, serial, config, logger, fatal, fatal_recovery):
            return False

        redis.update_state(State.remove_state_add_IDLE, state)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True
