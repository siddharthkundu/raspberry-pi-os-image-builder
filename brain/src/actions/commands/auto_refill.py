from typing import List
import logging

from common.enums import State
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager
from actions.commands.get_water_level import GetWaterLevelCommand
from actions.commands.move import MoveCommand


class AutoRefillCommand:

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

        def remove_state_and_send_feedback():
            redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
            if action.get('NeedsFeedbackOnSuccess', False):
                logger.send_event(logging.INFO)
                feedback_manager.send_to_gateway(instruction, action, memory)

        redis.update_state(State.add_state_remove_IDLE, State.NON_SENSITIVE_ACTION)

        if not GetWaterLevelCommand.run(instruction, {'val': ['16']}, error_handler_factory, feedback_manager,
                                        memory, redis, serial, config, logger, fatal, fatal_recovery):
            logger.log_system(logging.FATAL, 'Failed to read water level!')
            logger.log_system(logging.FATAL,
                              'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            logger.add_to_event(statusCode='readWaterLevelError',
                                error_message='Failed to read water level!')
            logger.send_event(logging.FATAL)
            exit(-6)

        if memory.post_tank_level <= 26:  # Avoid flooding the sensor
            logger.log_system(logging.INFO, 'Tank is near full. Not doing a Refill.')
            logger.add_to_event(refill_message='Tank is near full. Not doing a Refill.')
            remove_state_and_send_feedback()
            return True

        if 'workingStations' in instruction and instruction['type'] == "AUTOREFILL":
            station_locations = [int(y) for y in instruction['workingStations']]

            # Get_Pos
            x_pos, y_pos, _ = redis.get_position()

            # Calculate nearest station
            if y_pos not in station_locations:
                diff: List[int] = [abs(y_pos - loc) for loc in station_locations]
                y_target: int = station_locations[diff.index(min(diff))]

                # Move to the nearest station
                move_command = [0, int(x_pos % 256), int(x_pos / 256), int(y_target % 256), int(y_target / 256),
                                0, 0, 50]
                if not MoveCommand.run(instruction, {'val': move_command}, error_handler_factory, feedback_manager,
                                       memory, redis, serial, config, logger, fatal, fatal_recovery):
                    logger.log_system(logging.FATAL, 'Failed to move to the watering station as {y_target}!')
                    logger.log_system(logging.FATAL,
                                      'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
                    logger.add_to_event(statusCode='moveToWateringStationError',
                                        error_message='Failed to move to the watering station as {y_target}!')
                    redis.del_position()
                    logger.send_event(logging.FATAL)
                    exit(-7)

            y_pos = redis.get_axis_position('y')
            logger.log_system(logging.INFO, f'Auto Refill -- Refilling at station Y-{y_pos}')
            logger.add_to_event(refill_message=f'Refilling at station Y-{y_pos}')

        serial.send([int(x) for x in action['val']])
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            logger.log_system(logging.FATAL, 'Horizontal Robot failed while auto refill!')
            logger.log_system(logging.FATAL,
                              'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            logger.add_to_event(statusCode='HorizontalBotAutoRefillError',
                                error_message='Horizontal Robot failed while auto refill!',
                                firmware_errors=[
                                    error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)
                                ])
            logger.send_event(logging.FATAL)
            exit(-8)

        answer = {}
        answer['Left'] = [x.decode('utf-8') for x in left_answer]
        answer['Right'] = [x.decode('utf-8') for x in right_answer]

        remove_state_and_send_feedback()

        return True
