from typing import Callable, List, Optional
import logging

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager
from actions.commands.get_position import GetPositionCommand


class MoveCommand:
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

        custom_speed: Optional[int] = memory.custom_speed

        command_str: List[str] = [str(v) for v in action['val']]
        if custom_speed:
            command_str = command_str[:6] + [str(custom_speed)] + command_str[7:]
        if command_str[1] == '-':
            state_to_add: State = State.MOVING_Y | State.MOVING_Z_DOWN | State.MOVING_Z_UP
            x = redis.get_axis_position('x')
            command_str = [command_str[0]] + [str(x % 256), str(int(x / 256))] + command_str[2:]
        elif command_str[1].startswith('['):
            state_to_add = State.MOVING_X
            instruction_id: str = instruction.get('instructionId', '')
            bytes_str_to_int: Callable[[str, str], int] = lambda a, b: int(a) + int(b) * 256
            choices = [bytes_str_to_int(*choice.split('_')) for choice in command_str[1][1:-1].split('|')]
            if instruction_id != memory.current_instruction_id:
                memory.current_instruction_id = instruction_id
                current_x = redis.get_axis_position('x')
                memory.current_choice = 0 if abs(choices[0] - current_x) < abs(choices[1] - current_x) else 1
            command_str = [command_str[0]] + [str(choices[memory.current_choice] % 256),
                                              str(int(choices[memory.current_choice] / 256))] + command_str[2:]
        else:
            state_to_add = State.MOVING_X | State.MOVING_Y | State.MOVING_Z_DOWN | State.MOVING_Z_UP
        redis.update_state(State.add_state_remove_IDLE, state_to_add)

        command = [int(x) for x in command_str]

        serial.send(command)
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotMoveError',
                'message': 'Horizontal Robot failed while moving'
            }
            logger.add_to_event(
                statusCode=details['statusCode'],
                error_message=details['message'],
                firmware_errors=[
                    error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)
                ])
            error_handler(instruction, action)
            redis.update_state(State.remove_state_add_IDLE, state_to_add)
            # later on more detailed description
            logger.log_system(logging.ERROR, details['message'])
            logger.send_event(logging.ERROR)
            feedback_manager.send_to_gateway(instruction, action, memory, details)
            return False

        logger.log_system(logging.INFO, f'Left: {left_answer}\n\tRight: {right_answer}')

        if not GetPositionCommand.run(instruction, {'val': ['9']}, error_handler_factory, feedback_manager, memory,
                                      redis, serial, config, logger, fatal, fatal_recovery):
            return False

        redis.update_state(State.remove_state_add_IDLE, state_to_add)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True
