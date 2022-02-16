from typing import Any, Callable, Dict, Union
import json

from common.mqtt_client import MQTT
from common.config import Config
from common.serial_manager import SerialManagerAbstract
from common.redis_client import Redis
from common.log_event import Logger
from common.enums import State
from common.types import Instruction, Command, Feedback
from actions.memory import Memory


class FeedbackManager:
    def __init__(self, memory: Memory, mqtt: MQTT, serial: SerialManagerAbstract, redis: Redis,
                 config: Config, logger: Logger) -> None:
        self._memory: Memory = memory
        self._mqtt: MQTT = mqtt
        self._serial: SerialManagerAbstract = serial
        self._redis: Redis = redis
        self._config: Config = config
        self._logger: Logger = logger

    def send_to_gateway(self,
                        instruction: Instruction,
                        action: Command,
                        memory: Memory,
                        additional_details: Dict[str, Any] = {}) -> None:

        feedback: Dict[str, Any] = {}
        feedback['Meta'] = {}
        feedback['Meta']['Instruction'] = instruction
        feedback['Meta']['Command'] = action

        feedback['gutterId'] = feedback['Meta']['Instruction'].get('gutterId', '')
        feedback['instructionId'] = feedback['Meta']['Instruction'].get('instructionId', '')
        feedback['instructionDatetime'] = feedback['Meta']['Instruction'].get('startDateTime', '')
        feedback['instructionType'] = feedback['Meta']['Instruction'].get('type', 'manual')
        feedback['instructionStartTime'] = feedback['Meta']['Instruction'].get('startTime', '')

        feedback['instructionStatus'] = 'FAILED' if 'statusCode' in additional_details else 'SUCCESSFUL'
        feedback = {**feedback, **additional_details}
        self.fill_details(feedback, memory)

        self._mqtt.send(f'rc/{self._config.stage}/farms/{self._config.farm_id}/robots/{self._config.robot_id}/feedback',
                        json.dumps(feedback))
        self._redis.update_state(State.remove_state, State.HANDLING_INSTRUCTION)

    def fill_details_exit_success(self, _: Feedback, memory: Memory) -> None:
        pass

    def fill_details_exit_fail(self, _: Feedback, memory: Memory) -> None:
        pass

    def set_layer_slot_destination(self, feedback: Feedback):
        feedback['layerId'] = feedback['Meta']['Instruction']['layerIdDestination']
        feedback['slotId'] = feedback['Meta']['Instruction']['slotIdDestination']

    def set_cell_layer_slot_source_destination(self, feedback: Feedback):
        feedback['cellId'] = feedback['Meta']['Instruction']['cellId']
        feedback['layerId'] = feedback['Meta']['Instruction']['layerId']
        feedback['slotId'] = feedback['Meta']['Instruction']['slotId']
        feedback['cellIdDestination'] = feedback['Meta']['Instruction']['cellIdDestination']
        feedback['layerIdDestination'] = feedback['Meta']['Instruction']['layerIdDestination']
        feedback['slotIdDestination'] = feedback['Meta']['Instruction']['slotIdDestination']

    def fill_details_onboard_success(self, feedback: Feedback, memory: Memory) -> None:
        feedback['cellId'] = feedback['Meta']['Instruction']['cellIdDestination']
        self.set_layer_slot_destination(feedback)

    def fill_details_onboard_fail(self, feedback: Feedback, memory: Memory) -> None:
        feedback['cellId'] = feedback['Meta']['Instruction']['cellIdDestination']
        self.set_layer_slot_destination(feedback)

    def _set_feedback_for_rfid_and_location(self, feedback: Feedback, memory: Memory) -> None:
        feedback['layerId'] = feedback['Meta']['Instruction']['layerId']
        feedback['slotId'] = feedback['Meta']['Instruction']['sourceSlotId']
        feedback['rfid'] = memory.current_rfid
        feedback['farmId'] = feedback['Meta']['Instruction']['farmId']

    def fill_details_scan_to_onboard_success(self, feedback: Feedback, memory: Memory) -> None:
        self._set_feedback_for_rfid_and_location(feedback, memory)

    def fill_details_scan_to_onboard_fail(self, feedback: Feedback, memory: Memory) -> None:
        self._set_feedback_for_rfid_and_location(feedback, memory)

    def _set_cell_layer_slot_destination_and_rfid(self, feedback: Feedback, memory: Memory) -> None:
        feedback['layerId'] = feedback['Meta']['Instruction']['layerIdDestination']
        feedback['slotId'] = feedback['Meta']['Instruction']['slotIdDestination']
        feedback['cellId'] = feedback['Meta']['Instruction']['cellIdDestination']
        feedback['gutterId'] = memory.current_rfid

    def fill_details_move_success(self, feedback: Feedback, memory: Memory) -> None:
        self._set_cell_layer_slot_destination_and_rfid(feedback, memory)

    def fill_details_move_fail(self, feedback: Feedback, memory: Memory) -> None:
        self._set_cell_layer_slot_destination_and_rfid(feedback, memory)

    def fill_details_photo_success(self, _: Feedback, memory: Memory) -> None:
        pass

    def fill_details_photo_fail(self, _: Feedback, memory: Memory) -> None:
        pass

    def fill_details_water_success(self, feedback: Feedback, memory: Memory) -> None:
        feedback['preWateringWeight'] = memory.pre_weight
        feedback['postWateringWeight'] = memory.post_weight
        feedback['preWateringTankLevel'] = memory.pre_tank_level
        feedback['postWateringTankLevel'] = memory.post_tank_level

    def fill_details_water_fail(self, _: Feedback, memory: Memory) -> None:
        pass

    def fill_details_show(self, feedback: Feedback, memory: Memory) -> None:
        self.set_cell_layer_slot_source_destination(feedback)

    def fill_details_return(self, feedback: Feedback, memory: Memory) -> None:
        self.set_cell_layer_slot_source_destination(feedback)

    def _set_farm_cell_layer_slot(self, feedback: Feedback, memory: Memory) -> None:
        feedback['farmId'] = feedback['Meta']['Instruction']['farmId']
        feedback['cellId'] = feedback['Meta']['Instruction']['cellId']
        feedback['layerId'] = feedback['Meta']['Instruction']['layerId']
        feedback['slotId'] = feedback['Meta']['Instruction']['slotId']

    def fill_details_validate_success(self, feedback: Feedback, memory: Memory) -> None:
        self._set_farm_cell_layer_slot(feedback, memory)
        if memory.current_rfid != 'invalid_rfid':
            feedback['gutterId'] = memory.current_rfid
        if memory.post_weight > 2000:
            feedback['weight'] = memory.post_weight

    def fill_details_validate_fail(self, feedback: Feedback, memory: Memory) -> None:
        self._set_farm_cell_layer_slot(feedback, memory)

    def fill_details(self, feedback: Feedback, memory: Memory) -> None:
        detail_dict: Dict[str, Callable[[Feedback, Memory], None]] = {
            "WATER_FAILED": self.fill_details_water_fail,
            "WATER_SUCCESSFUL": self.fill_details_water_success,
            "PHOTO_FAILED": self.fill_details_photo_fail,
            "PHOTO_SUCCESSFUL": self.fill_details_photo_success,
            "ONBOARD_FAILED": self.fill_details_onboard_fail,
            "ONBOARD_SUCCESSFUL": self.fill_details_onboard_success,
            "SCAN_TO_ONBOARD_FAILED": self.fill_details_scan_to_onboard_fail,
            "SCAN_TO_ONBOARD_SUCCESSFUL": self.fill_details_scan_to_onboard_success,
            "MOVE_FAILED": self.fill_details_move_success,
            "MOVE_SUCCESSFUL": self.fill_details_move_fail,
            "EXIT_FAILED": self.fill_details_exit_fail,
            "EXIT_SUCCESSFUL": self.fill_details_exit_success,
            "SHOW_SUCCESSFUL": self.fill_details_show,
            "SHOW_FAILED": self.fill_details_show,
            "RETURN_SUCCESSFUL": self.fill_details_return,
            "RETURN_FAILED": self.fill_details_return,
            "VALIDATE_SUCCESSFUL": self.fill_details_validate_success,
            "VALIDATE_FAILED": self.fill_details_validate_fail,
        }
        detail_dict.get(f"{feedback['instructionType']}_{feedback['instructionStatus']}", lambda a, b: None)(feedback,
                                                                                                             memory)
