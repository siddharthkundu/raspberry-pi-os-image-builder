import logging

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager


class TareCommand:
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

        redis.update_state(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION)
        standard_error_handler = error_handler_factory(ErrorHandlerCode.STANDARD)

        serial.send([int(x) for x in action['val']])
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotTareError',
                'message': 'Horizontal Robot failed while tareing'
            }
            logger.add_to_event(
                statusCode=details['statusCode'],
                error_message=details['message'],
                firmware_errors=[
                    error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)
                ])
            standard_error_handler(instruction, action)
            redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)

            logger.log_system(logging.ERROR, details['message'])
            logger.send_event(logging.ERROR)
            feedback_manager.send_to_gateway(instruction, action, memory, details)
            return False

        redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True
