import json
import logging
from typing import List

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager
from model.position import Position


class GetPositionCommand:

    SERIAL_MESSAGES: List[int] = [9]

    def __init__(self, serial: SerialManager):
        self._serial = serial

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
        reset_z_error_handler = error_handler_factory(ErrorHandlerCode.RESET_Z)

        serial.send([int(x) for x in action['val']])
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotGetPosError',
                'message': 'Horizontal Robot failed while getting position'
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

        answer = {}
        answer['Left'] = [x.decode('utf-8') for x in left_answer]
        answer['Right'] = [x.decode('utf-8') for x in right_answer]

        logger.log_system(logging.INFO, f'Position: {json.dumps(answer)}')

        x = int(right_answer[2])
        y = int(left_answer[2])
        z_1 = int(right_answer[3])
        z_2 = int(left_answer[3])

        if z_1 != z_2:
            details = {
                'statusCode': 'zAxisUnsyncWarning',
                'message': 'z-Axis seems not be in sink.'
            }
            reset_z_error_handler(instruction, action)
            logger.log_system(logging.WARN, 'z-Axis seems not be in sink.')
            logger.prepare_listitem_for_event(statusCode=details['statusCode'], warning_message=details['message'])
            logger.add_listitem_to_event('warnings')

        redis.set_position(x, y, z_1)

        redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True

    def get_position(self) -> Position:
        self._serial.send(GetPositionCommand.SERIAL_MESSAGES)
        (left_answer, right_answer) = self._serial.receive()

        if not self._serial.is_ok(left_answer, right_answer):
            raise RuntimeError('Serial Communication is not ok')
        # TODO the serial communication is common to every command. We should add an abstract method

        x = int(right_answer[2])
        y = int(left_answer[2])
        z_1 = int(right_answer[3])
        z_2 = int(left_answer[3])
        if z_1 != z_2:
            raise RuntimeError('The 2 grippers are not aligned')

        return Position(x, y, z_1)
