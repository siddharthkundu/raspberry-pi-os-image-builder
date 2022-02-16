import logging
from typing import Any, Callable, List

from actions.commands.home import HomeCommand
from actions.commands.move import MoveCommand
from actions.commands.pause import PauseCommand
from actions.commands.set_pumps import SetPumpsCommand
from actions.feedback.feedback_manager import FeedbackManager
from actions.memory import Memory
from common.config import Config
from common.enums import State, ErrorHandlerCode
from common.log_event import Logger
from common.redis_client import Redis
from common.serial_manager import SerialManagerAbstract
from common.types import Command, Instruction, ErrorHandlerFactoryFunc


class ErrorHandler:
    def __init__(self,
                 memory: Memory,
                 feedback_manager: FeedbackManager,
                 serial: SerialManagerAbstract,
                 redis: Redis,
                 config: Config,
                 logger: Logger,
                 cancel: Callable[[Instruction, Command, ErrorHandlerFactoryFunc, FeedbackManager, Memory, Redis,
                                   SerialManagerAbstract, Config, Logger, bool, bool], bool]) -> None:

        self._redis = redis
        self._config = config
        self._logger = logger
        self._memory = memory

        self._dependencies: List[Any] = [
            feedback_manager,
            memory,
            redis,
            serial,
            config,
            logger
        ]

        self._cancel = cancel

    def get_handler(self, code: ErrorHandlerCode) -> Callable[[Instruction, Command], None]:
        return {
            ErrorHandlerCode.FATAL_HOMING: self.fatal_handler_homing,
            ErrorHandlerCode.FATAL_RECOVERY_HOMING: self.fatal_handler_recovery_homing,
            ErrorHandlerCode.FATAL_MOVING: self.fatal_handler_moving,
            ErrorHandlerCode.FATAL_RECOVERY_MOVING: self.fatal_handler_recovery_moving,
            ErrorHandlerCode.FATAL_RECOVERY_PAUSE: self.fatal_handler_recovery_pause,
            ErrorHandlerCode.FATAL_RECOVERY_SET_PUMPS: self.fatal_handler_recovery_set_pumps,
            ErrorHandlerCode.FATAL_SET_POS: self.fatal_handler_set_pos,
            ErrorHandlerCode.STANDARD: self.standard_error_handler,
            ErrorHandlerCode.RESET_Z: self.reset_z_error_handler,
            ErrorHandlerCode.NOOP: self.noop_handler
        }[code]

    def fatal_handler_homing(self, instruction: Instruction, command: Command) -> None:
        self._logger.log_system(logging.FATAL, 'Something went wrong on startup while homing!')
        self._logger.log_system(logging.FATAL,
                                'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
        self._logger.add_to_event(criticalStatusCode='startupHomingError',
                                  criticaErrorMessage='Something went wrong on startup while homing!')
        self._logger.send_event(logging.FATAL)
        self._redis.del_position()
        exit(-5)

    def fatal_handler_recovery_homing(self, instruction: Instruction, command: Command) -> None:
        self._logger.log_system(logging.FATAL, 'Something went wrong on recovery while homing!')
        self._logger.log_system(logging.FATAL,
                                'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
        self._logger.add_to_event(criticalStatusCode='recoveryHomingError',
                                  criticaErrorMessage='Something went wrong on recovery while homing!')
        self._logger.send_event(logging.FATAL)
        self._redis.del_position()
        exit(-5)

    def fatal_handler_moving(self, instruction: Instruction, command: Command) -> None:
        pos = self._redis.get_position()
        if pos:
            x, y, z = pos
            if len(command['val']) == 7:
                x_to_bytes = command['val'][1][1:-1].split('|')[self._memory.current_choice].split('_')
                x_to = int(x_to_bytes[0]) + int(x_to_bytes[1]) * 256
                y_to = int(command['val'][2]) + int(command['val'][3]) * 256
                z_to = int(command['val'][4]) + int(command['val'][5]) * 256
            else:
                x_to = int(command['val'][1]) + int(command['val'][2]) * 256
                y_to = int(command['val'][3]) + int(command['val'][4]) * 256
                z_to = int(command['val'][5]) + int(command['val'][6]) * 256

            self._logger.log_system(logging.FATAL,
                                    f'Something went wrong on startup while moving from x: {x} y: {y} z: {z} '
                                    f'to x: {x_to} y: {y_to} z: {z_to}! :(')
            self._logger.log_system(logging.FATAL,
                                    'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            self._logger.add_to_event(criticalStatusCode='startupMovingError',
                                      criticaErrorMessage=f'Something went wrong on startup while moving '
                                                          f'from x: {x} y: {y} z: {z} '
                                                          f'to x: {x_to} y: {y_to} z: {z_to}! :(')
            self._logger.send_event(logging.FATAL)
        else:
            self._logger.log_system(logging.FATAL, 'Something went wrong on startup while moving! :(')
            self._logger.log_system(logging.FATAL,
                                    'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            self._logger.add_to_event(criticalStatusCode='startupMovingError',
                                      criticaErrorMessage='Something went wrong on startup while moving! :(')
            self._logger.send_event(logging.FATAL)
        exit(-5)

    def fatal_handler_recovery_moving(self, instruction: Instruction, command: Command) -> None:
        pos = self._redis.get_position()
        if pos:
            x, y, z = pos
            if len(command['val']) == 7:
                x_to_bytes = command['val'][1][1:-1].split('|')[self._memory.current_choice].split('_')
                x_to = int(x_to_bytes[0]) + int(x_to_bytes[1]) * 256
                y_to = int(command['val'][2]) + int(command['val'][3]) * 256
                z_to = int(command['val'][4]) + int(command['val'][5]) * 256
            else:
                x_to = int(command['val'][1]) + int(command['val'][2]) * 256
                y_to = int(command['val'][3]) + int(command['val'][4]) * 256
                z_to = int(command['val'][5]) + int(command['val'][6]) * 256

            self._logger.log_system(logging.FATAL,
                                    f'Something went wrong on recovery while moving from x: {x} y: {y} z: {z} '
                                    f'to x: {x_to} y: {y_to} z: {z_to}! :(')
            self._logger.log_system(logging.FATAL,
                                    'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            self._logger.add_to_event(criticalStatusCode='recoveryMovingError',
                                      criticaErrorMessage=f'Something went wrong on recovery while moving '
                                                          f'from x: {x} y: {y} z: {z} '
                                                          f'to x: {x_to} y: {y_to} z: {z_to}! :(')
            self._logger.send_event(logging.FATAL)
        else:
            self._logger.log_system(logging.FATAL, 'Something went wrong on recovery while moving! :(')
            self._logger.log_system(logging.FATAL,
                                    'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            self._logger.add_to_event(criticalStatusCode='recoveryMovingError',
                                      criticaErrorMessage='Something went wrong on recovery while moving! :(')
            self._logger.send_event(logging.FATAL)
        exit(-5)

    def fatal_handler_recovery_pause(self, instruction: Instruction, command: Command) -> None:
        self._logger.log_system(logging.FATAL, 'Something went wrong on recovery while sleeping!')
        self._logger.log_system(logging.FATAL,
                                'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
        self._logger.add_to_event(criticalStatusCode='recoveryPauseError',
                                  criticaErrorMessage='Something went wrong on recovery while sleeping!')
        self._logger.send_event(logging.FATAL)
        exit(-5)

    def fatal_handler_recovery_set_pumps(self, instruction: Instruction, command: Command) -> None:
        self._logger.log_system(logging.FATAL, 'Something went wrong on recovery while setting pumps!')
        self._logger.log_system(logging.FATAL,
                                'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
        self._logger.add_to_event(criticalStatusCode='recoverySetPumpsError',
                                  criticaErrorMessage='Something went wrong on recovery while setting pumps!')
        self._logger.send_event(logging.FATAL)
        exit(-5)

    def fatal_handler_set_pos(self, instruction: Instruction, command: Command) -> None:
        self._logger.log_system(logging.FATAL, 'Something went wrong while setting position!')
        self._logger.log_system(logging.FATAL,
                                'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
        self._logger.add_to_event(criticalStatusCode='settingPositionError',
                                  criticaErrorMessage='Something went wrong while setting position!')
        self._logger.send_event(logging.FATAL)
        self._redis.del_position()
        exit(-5)

    def noop_handler(self, instruction: Instruction, command: Command) -> None:
        pass

    def reset_z_error_handler(self, instruction: Instruction, command: Command) -> None:
        pos = self._redis.get_position()
        x, y, _ = [[axis % 256, int(axis / 256)] for axis in (pos if pos else [0, 0, 0])]
        if pos:
            MoveCommand.run(instruction, {'val': [0] + x + y + [50, 0, 100]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        HomeCommand.run(instruction, {'val': [7, 0, 0, 0, 0, 1, 0, 20]}, self.get_handler,
                        *self._dependencies, fatal_recovery=True)

    def standard_error_handler(self, instruction: Instruction, command: Command) -> None:
        PauseCommand.run(instruction, {'val': [3, 2]}, self.get_handler, *self._dependencies, fatal_recovery=True)
        state = self._redis.get_current_state()
        if not State.has_state(state, State.HOMING_Y | State.MOVING_Y):
            HomeCommand.run(instruction, {'val': [7, 0, 0, 0, 0, 1, 0, 20]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        pos = self._redis.get_position()
        x, y, z = [[axis % 256, int(axis / 256)] for axis in (pos if pos else [0, 0, 0])]
        if State.has_state(state, State.TOGGLE_PUMPS_ON):
            SetPumpsCommand.run(instruction, {'val': [2, 0, 0, 0, 0, 0, 0]}, self.get_handler,
                                *self._dependencies, fatal_recovery=True)
            HomeCommand.run(instruction, {'val': [7, 0, 0, 0, 0, 1, 0, 20]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        if State.has_state(state, State.MOVING_X | State.HOMING_X):
            if pos:
                MoveCommand.run(instruction, {'val': [0, 0, 0] + y + z + [100]}, self.get_handler,
                                *self._dependencies, fatal_recovery=True)
            HomeCommand.run(instruction, {'val': [7, 1, 0, 0, 0, 0, 0, 20]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        if State.has_state(state, State.MOVING_Z_UP | State.MOVING_Z_DOWN | State.HOMING_Z):
            if pos:
                MoveCommand.run(instruction, {'val': [0] + x + y + [0, 0, 100]}, self.get_handler,
                                *self._dependencies, fatal_recovery=True)
            HomeCommand.run(instruction, {'val': [7, 0, 0, 0, 0, 1, 0, 20]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        if State.has_state(state, State.HOMING_Y | State.MOVING_Y):
            if pos:
                MoveCommand.run(instruction, {'val': [0] + x + [114, 56] + z + [100]}, self.get_handler,
                                *self._dependencies, fatal_recovery=True)
            HomeCommand.run(instruction, {'val': [7, 0, 0, 2, 0, 0, 0, 20]}, self.get_handler,
                            *self._dependencies, fatal_recovery=True)
        self._cancel(instruction, {}, self.get_handler, *self._dependencies)
