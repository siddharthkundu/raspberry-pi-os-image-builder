import json
import logging
import threading
import time
from collections import deque
from typing import (Any, Callable, Deque, Dict, List, Tuple, cast)

from actions.commands.auto_refill import AutoRefillCommand
from actions.commands.get_gripsense import GetGripsenseCommand
from actions.commands.get_position import GetPositionCommand
from actions.commands.get_settings import GetSettingsCommand
from actions.commands.get_water_level import GetWaterLevelCommand
from actions.commands.home import HomeCommand
from actions.commands.move import MoveCommand
from actions.commands.pause import PauseCommand
from actions.commands.scan_rfid import ScanRFIDCommand
from actions.commands.set_magnet import SetMagnetCommand
from actions.commands.set_position import SetPositionCommand
from actions.commands.set_pumps import SetPumpsCommand
from actions.commands.set_settings import SetSettingsCommand
from actions.commands.side_camera import SideCam
from actions.commands.tare import TareCommand
from actions.commands.top_camera import TopCam
from actions.commands.water import WaterCommand
from actions.commands.weight import WeightCommand
from actions.errors.error_handler import ErrorHandler
from actions.feedback.feedback_manager import FeedbackManager
from actions.feedback.idle_handler import IdleHandler
from actions.memory import Memory
from common.Interval import Interval
from common.config import Config
from common.enums import State
from common.log_event import Logger
from common.mqtt_client import MQTT
from common.redis_client import Redis
from common.serial_manager import SerialManagerAbstract
from common.types import Command, Instruction, ErrorHandlerFactoryFunc
from util import Try


class ActionManager:
    def __init__(self, serial: SerialManagerAbstract, mqtt: MQTT, redis: Redis, config: Config,
                 logger: Logger) -> None:
        self._config: Config = config
        self._logger: Logger = logger
        self._serial: SerialManagerAbstract = serial
        self._mqtt: MQTT = mqtt
        self._redis: Redis = redis
        self._memory: Memory = Memory()
        self._feedback_manager: FeedbackManager = FeedbackManager(self._memory, mqtt, serial, redis, config, logger)
        self._error_handler: ErrorHandler = ErrorHandler(self._memory, self._feedback_manager, self._serial, redis,
                                                         config, logger, self.cancel_all_actions)
        self._debug_only: bool = config.debug_only_serialless

        self._queue: Deque[Tuple[Instruction, Command]] = deque()

        self._resolver: Dict[int,
                             Callable[[Instruction,
                                      Command,
                                      ErrorHandlerFactoryFunc,
                                      FeedbackManager,
                                      Memory,
                                      Redis,
                                      SerialManagerAbstract,
                                      Config,
                                      Logger,
                                      bool,
                                      bool],
                                      bool]] = \
            {
                0: MoveCommand.run,
                1: WeightCommand.run,
                2: WaterCommand.run,
                3: PauseCommand.run,
                6: ScanRFIDCommand.run,
                7: HomeCommand.run,
                8: SetPositionCommand.run,
                9: GetPositionCommand.run,
                12: GetSettingsCommand.run,
                13: SetSettingsCommand.run,
                15: GetGripsenseCommand.run,
                16: GetWaterLevelCommand.run,
                17: SetMagnetCommand.run,
                20: AutoRefillCommand.run,
                21: SetPumpsCommand.run,
                22: TareCommand.run,
                100: TopCam.open,
                101: TopCam.take_image,
                102: TopCam.close,
                105: SideCam.open,
                106: SideCam.take_image,
                107: SideCam.close,
                255: self.cancel_all_actions
        }

        self._dependencies: List[Any] = [
            self._feedback_manager,
            self._memory,
            self._redis,
            self._serial,
            self._config,
            self._logger
        ]

        state: State = self._redis.get_current_state()

        logger.create_event(f'Startup fresh {self._config.robot_id}', robot_id=self._config.robot_id)
        HomeCommand.run({}, {'val': [7, 1, 0, 0, 0, 0, 0, 80]}, self._error_handler.get_handler,
                        *self._dependencies, fatal=True)
        HomeCommand.run({}, {'val': [7, 1, 0, 0, 0, 0, 0, 20]}, self._error_handler.get_handler,
                        *self._dependencies, fatal=True)
        HomeCommand.run({}, {'val': [7, 0, 0, 0, 0, 1, 0, 20]}, self._error_handler.get_handler,
                        *self._dependencies, fatal=True)
        HomeCommand.run({}, {'val': [7, 0, 0, 2, 0, 0, 0, 80]}, self._error_handler.get_handler,
                        *self._dependencies, fatal=True)
        HomeCommand.run({}, {'val': [7, 0, 0, 2, 0, 0, 0, 20]}, self._error_handler.get_handler,
                        *self._dependencies, fatal=True)
        logger.send_event(logging.INFO)

        if State.has_state(state, State.HANDLING_INSTRUCTION):
            if not self._redis.get_log_item_state(logger):
                logger.create_event('Unknown', robot_id=self._config.robot_id)
            instruction, command = self._redis.get_current_action()
            details = {
                'statusCode': 'HorizontalBotRebootError',
                'message': 'Horizontal Robot rebooted while busy'
            }
            logger.log_system(logging.ERROR, details['message'])
            logger.add_to_event(statusCode=details['statusCode'], error_message=details['message'])
            logger.send_event(logging.ERROR)
            self._feedback_manager.send_to_gateway(instruction, command, self._memory, details)
        self._redis.set_state(State.IDLE)

        TopCam.setup(self._mqtt, self._logger, self._config)
        SideCam.setup(self._mqtt, self._logger, self._config)

        threading.Thread(target=self.handle_action_queue, daemon=True).start()

    def start_handling_instructions(self) -> None:
        def handle_instruction(topic: str, payload: str, **kwargs: str) -> None:
            self._redis.update_state(State.add_state, State.HANDLING_INSTRUCTION)

            self._logger.log_system(logging.INFO, 'Received: ' + json.dumps(json.loads(payload), indent=4))
            actions = json.loads(payload)

            self._logger.create_event('start handling instruction', robot_id=self._config.robot_id,
                                      id=actions['Instruction']['instructionId'], type=actions['Instruction']['type'])

            for command in actions['Commands']:
                command['val'] = cast(str, command['Str']).split(' ')
                self.parse_and_handle_action(actions['Instruction'], command)

        self._mqtt.subscribe(f'rc/{self._config.stage}/robots/{self._config.robot_id}/cmds', handle_instruction)

    def parse_and_handle_action(self, instruction: Instruction, action: Command) -> None:
        self._queue.appendleft((instruction, action))

    # Todo: look over it again
    def handle_action_queue(self) -> None:
        self._logger.log_system(logging.INFO, 'Start handling action queue')
        idle_handler = IdleHandler(self._mqtt, self._config.stage, self._config.farm_id, self._config.robot_id,
                                   self._logger)
        water_level_command = GetWaterLevelCommand(self._serial)
        get_position_command = GetPositionCommand(self._serial)

        interval = Interval(self._config.idle_time_sec, idle_handler.send_message,
                            lambda: (self._redis.get_current_action(), Try(water_level_command.get_water_level),
                                     Try(get_position_command.get_position)))
        while True:
            if len(self._queue) == 0:
                time.sleep(2)
                continue
            instruction, current_action = self._queue[-1]
            self._redis.set_current_action(instruction, current_action)
            self._queue.pop()
            id = instruction.get('instructionId', 'No instruction id')
            instruction_type = instruction.get('type', 'No instruction type')
            self._logger.log_system(
                logging.INFO, f'Current Action [{instruction_type}|{id}]:\n{json.dumps(current_action, indent=4)}')
            current_action_type = int(current_action['val'][0])
            if current_action_type not in self._resolver:
                self._logger.log_system(logging.ERROR, f'ActionType {current_action_type} not implemented -> skip!')
                continue
            if current_action and self._resolver[current_action_type](instruction, current_action,
                                                                      self._error_handler.get_handler,
                                                                      *self._dependencies):
                self._logger.log_system(logging.INFO, 'Ready for next Action')
            else:
                self._logger.log_system(logging.ERROR, 'Error of command, deleting actions.')

            if self._redis.get_current_state() != State.IDLE:
                interval.reset()

    def cancel_all_actions(self,
                           instruction: Instruction,
                           action: Command,
                           error_handler_factory: ErrorHandlerFactoryFunc,
                           feedback_manager: FeedbackManager,
                           memory: Memory,
                           redis: Redis,
                           serial: SerialManagerAbstract,
                           config: Config,
                           logger: Logger,
                           fatal: bool = False,
                           fatal_recovery: bool = False) -> bool:
        self._queue.clear()
        return True
