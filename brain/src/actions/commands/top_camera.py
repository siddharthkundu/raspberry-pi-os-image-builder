from typing import Dict
import json
import time
import logging

from common.enums import State, ErrorHandlerCode
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from common.mqtt_client import MQTT
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager


def topcam_error_handler(instruction: Instruction,
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


class TopCam:
    mqtt: MQTT = None
    cam_feedback = None
    feedback_timeout: int = 60  # seconds

    @staticmethod
    def setup(mqtt: MQTT, logger: Logger, config: Config):

        TopCam.mqtt = mqtt

        def topcam_feedback_callback(topic: str, payload: str, **kwargs: str) -> None:
            logger.log_system(logging.INFO, 'Received from TopCam: ' + json.dumps(json.loads(payload), indent=4))
            TopCam.cam_feedback = json.loads(payload)

        TopCam.mqtt.subscribe(f"rc/{config.stage}/robots/{config.robot_id}/cameras/top/feedback",
                              topcam_feedback_callback)

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

        TopCam.cam_feedback = None
        cam_command = {'instructionId': instruction['instructionId'],
                       'Str': 'open_cam'}
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        TopCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/top/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < TopCam.feedback_timeout and not TopCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not TopCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from TopCam")
            details = {'statusCode': 'HorizontalBotOpenTopCamError',
                       'message': 'Horizontal Robot - No response from TopCam'}
            logger.prepare_listitem_for_event(camera_out="No response from TopCam")
            logger.add_listitem_to_event('serial')
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                 error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=TopCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if TopCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Open TopCam response: {TopCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotOpenTopCamError',
                       'message': f"Horizontal Robot - TopCam message: {TopCam.cam_feedback['message']}"}
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
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

        params = {'prefix': f"{memory.current_rfid}_x_{x}_y_{y}_z_{z}_{time.strftime('%Y_%m_%d_%H_%M_%S')}_top",
                  'RFID': memory.current_rfid,
                  'runID': time.strftime('%Y-%m-%d'),
                  'view': 'top',
                  'robot': config.robot_id,
                  'x': x, 'y': y, 'z': z}
        TopCam.cam_feedback = None
        cam_command = {'instructionId': instruction['instructionId'],
                       'Str': 'take_image',
                       'Metadata': params}
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        TopCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/top/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < TopCam.feedback_timeout and not TopCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not TopCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from TopCam")
            details = {'statusCode': 'HorizontalBotShootTopCamError',
                       'message': 'Horizontal Robot - No response from TopCam'}
            logger.prepare_listitem_for_event(camera_out="No response from TopCam")
            logger.add_listitem_to_event('serial')
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                 error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=TopCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if TopCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Take_image TopCam response: {TopCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotShootTopCamError',
                       'message': f"Horizontal Robot - TopCam message: {TopCam.cam_feedback['message']}"}
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
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
        TopCam.cam_feedback = None
        logger.prepare_listitem_for_event(camera_in=cam_command['Str'])
        TopCam.mqtt.send(f"rc/{config.stage}/robots/{config.robot_id}/cameras/top/cmds", json.dumps(cam_command))
        trys: int = 0
        while trys < TopCam.feedback_timeout and not TopCam.cam_feedback:
            trys += 1
            time.sleep(1)

        if not TopCam.cam_feedback:
            logger.log_system(logging.ERROR, "No response from TopCam")
            details = {'statusCode': 'HorizontalBotCloseTopCamError',
                       'message': 'Horizontal Robot - No response from TopCam'}
            logger.prepare_listitem_for_event(camera_out="No response from TopCam")
            logger.add_listitem_to_event('serial')
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                 error_handler_factory)
            return False

        logger.prepare_listitem_for_event(camera_out=TopCam.cam_feedback.get('message', ''))
        logger.add_listitem_to_event('serial')
        if TopCam.cam_feedback.get('instructionStatus', '') == 'FAILED':
            logger.log_system(logging.ERROR, f"Close TopCam response: {TopCam.cam_feedback['message']}")
            details = {'statusCode': 'HorizontalBotCloseTopCamError',
                       'message': f"Horizontal Robot - TopCam message: {TopCam.cam_feedback['message']}"}
            topcam_error_handler(instruction, action, details, feedback_manager, memory, redis, logger,
                                 error_handler_factory)
            return False

        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)
        return True
