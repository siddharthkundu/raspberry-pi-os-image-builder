import logging
from typing import Dict

from common.enums import State, ErrorHandlerCode, InstructionType
from common.redis_client import Redis
from common.serial_manager import SerialManager
from common.log_event import Logger
from common.config import Config
from common.types import Instruction, Command, ErrorHandlerFactoryFunc
from actions.memory import Memory
from actions.feedback.feedback_manager import FeedbackManager


class ScanRFIDCommand:
    @staticmethod
    def scanner_error_handler(instruction: Instruction,
                              action: Command,
                              details: Dict,
                              feedback_manager: FeedbackManager,
                              memory: Memory,
                              redis: Redis,
                              logger: Logger,
                              error_handler_factory: ErrorHandlerFactoryFunc) -> None:
        # standard_error_handler by default, to drop gutter
        logger.add_to_event(
            statusCode=details['statusCode'],
            error_message=details['message'],
            firmware_errors=details['firmware_errors'])
        error_handler_factory(ErrorHandlerCode.STANDARD)(instruction, action)
        redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)

        logger.log_system(logging.ERROR, details['message'])
        logger.send_event(logging.ERROR)
        feedback_manager.send_to_gateway(instruction, action, memory, details)

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

        serial.send([int(x) for x in action['val']])
        (left_answer, right_answer) = serial.receive()

        if not serial.is_ok(left_answer, right_answer):
            details = {
                'statusCode': 'HorizontalBotRFIDReadError',
                'message': 'Horizontal Robot failed while reading RFID',
                'firmware_errors': [error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)]
            }
            ScanRFIDCommand.scanner_error_handler(instruction, action, details, feedback_manager, memory, redis,
                                                  logger, error_handler_factory)
            return False

        try:
            memory.current_rfid = bytes(left_answer[2]).decode('utf-8').strip()
            memory.current_rfid = memory.current_rfid if memory.current_rfid != '0' else 'invalid_rfid'
        except Exception:
            memory.current_rfid = 'invalid_rfid'

        if instruction['type'] == InstructionType.SCAN_TO_ONBOARD.name and memory.current_rfid == 'invalid_rfid':
            details = {
                'statusCode': 'HorizontalBotRFIDReadError',
                'message': 'SCAN_TO_ONBOARD failed because of no RFID',
                'firmware_errors': [error.toJson() for error in serial.get_firmware_error(left_answer, right_answer)]
            }
            ScanRFIDCommand.scanner_error_handler(instruction, action, details, feedback_manager, memory, redis,
                                                  logger, error_handler_factory)
            return False

        if instruction['type'] == InstructionType.ONBOARD.name:
            if memory.current_rfid == 'invalid_rfid':
                details = {
                    'statusCode': 'HorizontalBotRFIDReadError',
                    'message': 'ONBOARD failed because of no RFID',
                    'firmware_errors': [err.toJson() for err in serial.get_firmware_error(left_answer, right_answer)]
                }
                ScanRFIDCommand.scanner_error_handler(instruction, action, details, feedback_manager, memory, redis,
                                                      logger, error_handler_factory)
                return False

            if instruction.get('gutterId', '') == '':
                details = {
                    'statusCode': 'HorizontalBotRFIDReadError',
                    'message': "Received ONBOARD instruction without gutterId.",
                    'firmware_errors': [err.toJson() for err in serial.get_firmware_error(left_answer, right_answer)]
                }
                ScanRFIDCommand.scanner_error_handler(instruction, action, details, feedback_manager, memory, redis,
                                                      logger, error_handler_factory)
                return False
            if memory.current_rfid != instruction.get('gutterId', ''):
                details = {
                    'statusCode': 'RFID != gutter_id',
                    'message': f"ONBOARD failed: expected- {instruction['gutterId']}, received- "
                               f"{memory.current_rfid}",
                    'firmware_errors': [err.toJson() for err in serial.get_firmware_error(left_answer, right_answer)]
                }
                ScanRFIDCommand.scanner_error_handler(instruction, action, details, feedback_manager, memory, redis,
                                                      logger, error_handler_factory)
                return False

        logger.add_to_event(rfid=memory.current_rfid)

        redis.update_state(State.remove_state_add_IDLE, State.NON_SENSITIVE_ACTION)
        if action.get('NeedsFeedbackOnSuccess', False):
            logger.send_event(logging.INFO)
            feedback_manager.send_to_gateway(instruction, action, memory)

        return True
