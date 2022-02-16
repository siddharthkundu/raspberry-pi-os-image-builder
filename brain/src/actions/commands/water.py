from typing import List
import logging

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager


class WaterCommand:
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

        standard_error_handler = error_handler_factory(ErrorHandlerCode.STANDARD)

        command_with_config: List[str] = action['val']
        command: List[int] = [int(x) for x in command_with_config[:7]]

        factor: float = float(command_with_config[7])
        distance: float = float(command_with_config[8])
        flow: float = float(command_with_config[9])
        target_weight: float = float(command_with_config[10])
        diff_weight: float = target_weight - memory.post_weight

        logger.add_to_event(
            watering_factor=factor,
            watering_distance=distance,
            watering_flow=flow,
            target_weight=target_weight,
            diff_weight=diff_weight)

        if config.disable_pump_weight_safety or diff_weight >= config.min_weight_target_difference_before_watering \
                and memory.post_weight >= config.min_weight_before_watering:

            diff_weight = diff_weight if diff_weight <= config.max_watering else config.max_watering
            memory.custom_speed = int(factor * distance * flow / (60 * diff_weight))
            memory.custom_speed = memory.custom_speed if memory.custom_speed <= config.max_speed_watering \
                else config.max_speed_watering

            if not config.disable_pump_weight_safety and \
                    diff_weight <= config.min_weight_target_difference_before_watering_full:
                memory.custom_speed = int(memory.custom_speed / 2)
                if command[4] == 1:
                    command[3] = 0
                if command[6] == 1:
                    command[5] = 0

        else:
            command[3] = 0
            command[5] = 0
            memory.custom_speed = None

        command[4] = 0
        command[6] = 0

        if memory.current_choice == 1:
            command[3], command[5] = command[5], command[3]

        if command[3] == 0 and command[5] == 0:
            memory.custom_speed = None
            redis.update_state(State.remove_state, State.TOGGLE_PUMPS_ON | State.IDLE)
        else:
            redis.update_state(State.add_state_remove_IDLE, State.TOGGLE_PUMPS_ON)

        serial.send(command)
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotWaterError',
                'message': 'Horizontal Robot failed while turning on pumps'
            }
            logger.add_to_event(
                statusCode=details['statusCode'],
                error_message=details['message'],
                firmware_errors=[
                    error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)
                ])
            standard_error_handler(instruction, action)
            redis.update_state(State.remove_state_add_IDLE, State.TOGGLE_PUMPS_ON)
            # later on more detailed description
            logger.log_system(logging.ERROR, details['message'])
            logger.send_event(logging.ERROR)
            feedback_manager.send_to_gateway(instruction, action, memory, details)
            return False

        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True
