import json
import logging
from typing import Tuple

from util import Try_
from common.log_event import Logger
from common.mqtt_client import MQTT

from common.types import Command, Instruction
from model.position import Position


class IdleMessage:
    def __init__(self, water_level: int, position: Position, current_action: Tuple[Instruction, Command]):
        self.waterLevel = water_level
        self.position = position
        self.currentAction = current_action

    def toJSON(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


class IdleHandler:
    def __init__(self, mqtt: MQTT, stage: str, farm_id: int, robot_id: int,
                logger: Logger) -> None:
        self.__mqtt = mqtt
        self.__stage = stage
        self.__farm_id = farm_id
        self.__robot_id = robot_id
        self.__logger = logger

    def send_message(self, current_action: Tuple[Instruction, Command], water_level: Try_[int], position: Try_[Position]) -> None:
        if water_level.isFailure or position.isFailure:
            return

        idle_message = IdleMessage(water_level.get(), position.get(), current_action)
        json_dump = idle_message.toJSON()
        self.__logger.log_system(logging.INFO,
                                 f'Farm: {self.__farm_id}, robot: {self.__robot_id}, idle message: {json_dump}')
        self.__logger.add_to_event(idleFarmId=self.__farm_id, idleRobotId=self.__robot_id, idleMessage=json_dump)
        self.__logger.send_event(logging.INFO)
        self.__mqtt.send(f'rc/{self.__stage}/farms/{self.__farm_id}/robots/{self.__robot_id}/idle',
                         json_dump)
