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


class GetWaterLevelCommand:
    SERIAL_MESSAGES: List[int] = [16]

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

        serial.send([int(x) for x in action['val']])
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotGetWaterLevelError',
                'message': 'Horizontal Robot failed while getting water level'
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

        memory.pre_tank_level = memory.post_tank_level
        memory.post_tank_level = int(answer['Right'][2])

        logger.log_system(logging.INFO, f'Water Level: {json.dumps(memory.post_tank_level)}')
        logger.add_to_event(pre_tank_level=memory.pre_tank_level, post_tank_level=memory.post_tank_level)

        if memory.post_tank_level > 100:  # possibly faulty sensor
            details = {'statusCode': 'HorizontalBotGetWaterLevelError',
                       'message': 'Horizontal Robot water level sensor failed'}
            logger.add_to_event(statusCode=details['statusCode'], error_message=details['message'])
            logger.log_system(logging.ERROR, details['message'])
            standard_error_handler(instruction, action)
            redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
            logger.send_event(logging.ERROR)
            feedback_manager.send_to_gateway(instruction, action, memory, details)
            return False

        redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True

    def get_water_level(self) -> int:
        self._serial.send(GetWaterLevelCommand.SERIAL_MESSAGES)
        (left_answer, right_answer) = self._serial.receive()

        if not self._serial.is_ok(left_answer, right_answer):
            raise RuntimeError('Serial Communication is not ok')
        # TODO the serial communication is common to every command. We should add an abstract method
        answer = {'Right': [x.decode('utf-8') for x in right_answer]}
        return int(answer['Right'][2])
