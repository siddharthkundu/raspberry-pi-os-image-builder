from typing import Dict
import json
import time
import logging

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.mqtt_client import MQTT
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager


def sidecam_error_handler(instruction: Instruction,
                          action: Command,
                          details: Dict,
                          feedback_manager: FeedbackManager,
                          memory: Memory,
                          redis: Redis,
                          logger: Logger,
                          error_handler_factory: ErrorHandlerFactoryFunc) -> None:
    logger.add_to_event(statusCode=details['statusCode'], error_message=details['message'])
    error_handler_factory(ErrorHandlerCode.STANDARD)(instruction, action)
    redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
    logger.log_system(logging.ERROR, details['message'])
    logger.send_event(logging.ERROR)
    feedback_manager.send_to_gateway(instruction, action, memory, details)


class SideCam:
    mqtt: MQTT = None
    cam_feedback = None
    feedback_timeout: int = 60  # seconds

    @staticmethod
    def setup(mqtt: MQTT, logger: Logger, config: Config):

        SideCam.mqtt = mqtt

        def sidecam_feedback_callback(topic: str, payload: str, **kwargs: str) -> None:
            logger.log_system(logging.INFO, 'Received from SideCam: ' + json.dumps(json.loads(payload), indent=4))
            SideCam.cam_feedback = json.loads(payload)

        SideCam.mqtt.subscribe(f"rc/{config.stage}/robots/{config.robot_id}/cameras/side/feedback",
                               sidecam_feedback_callback)

    @staticmethod
    def open(instruction: Instruction,
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

        SideCam.cam_feedback = None
        cam_command = {'instructionId': instruction['instructionId'],
                       'Str': 'open_cam'}
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        SideCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/side/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < SideCam.feedback_timeout and not SideCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not SideCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from SideCam")
            details = {'statusCode': 'HorizontalBotOpenSideCamError',
                       'message': 'Horizontal Robot - No response from SideCam'}
            logger.prepare_listitem_for_event(camera_out="No response from SideCam")
            logger.add_listitem_to_event('serial')
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=SideCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if SideCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Open SideCam response: {SideCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotOpenSideCamError',
                       'message': f"Horizontal Robot - SideCam message: {SideCam.cam_feedback['message']}"}
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)
        return True

    @staticmethod
    def take_image(instruction: Instruction,
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
        pos = redis.get_position()
        if pos:
            x, y, z = pos
        else:
            x = y = z = ''

        params = {'prefix': f"{memory.current_rfid}_x_{x}_y_{y}_z_{z}_{time.strftime('%Y_%m_%d_%H_%M_%S')}_side",
                  'RFID': memory.current_rfid,
                  'runID': time.strftime('%Y-%m-%d'),
                  'view': 'side',
                  'robot': config.robot_id,
                  'x': x, 'y': y, 'z': z}
        SideCam.cam_feedback = None
        cam_command = {'instructionId': instruction['instructionId'],
                       'Str': 'take_image',
                       'Metadata': params}
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        SideCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/side/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < SideCam.feedback_timeout and not SideCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not SideCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from SideCam")
            details = {'statusCode': 'HorizontalBotShootSideCamError',
                       'message': 'Horizontal Robot - No response from SideCam'}
            logger.prepare_listitem_for_event(camera_out="No response from SideCam")
            logger.add_listitem_to_event('serial')
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=SideCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if SideCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Take_image SideCam response: {SideCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotShootSideCamError',
                       'message': f"Horizontal Robot - SideCam message: {SideCam.cam_feedback['message']}"}
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)
        return True

    @staticmethod
    def close(instruction: Instruction,
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

        cam_command = {'instructionId': instruction['instructionId'],
                       'Str': 'close_cam'}
        SideCam.cam_feedback = None
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        SideCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/side/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < SideCam.feedback_timeout and not SideCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not SideCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from SideCam")
            details = {'statusCode': 'HorizontalBotCloseSideCamError',
                       'message': 'Horizontal Robot - No response from SideCam'}
            logger.prepare_listitem_for_event(camera_out="No response from SideCam")
            logger.add_listitem_to_event('serial')
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=SideCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if SideCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Close SideCam response: {SideCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotCloseSideCamError',
                       'message': f"Horizontal Robot - SideCam message: {SideCam.cam_feedback['message']}"}
            sidecam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                  error_handler_factory)
            return False

        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)
        return True
