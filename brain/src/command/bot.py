import os
import time
import logging

from actions.feedback.firmware_error_info import FirmwareErrorInfo
from common.log_event import Logger
from common.config import Config
from common.serial_manager import CreateSerialManager, SerialManagerAbstract
from actions.action_manager import ActionManager
from common.mqtt_client import MQTT
from common.redis_client import Redis


def main():
    root: str = os.environ.get('ROOT', '/home/pi/brain')
    stage: str = os.environ.get('STAGE', 'development')

    config: Config = Config(root, f'bot_{stage}.config', stage)
    firmware_error_info: FirmwareErrorInfo = FirmwareErrorInfo(f'{root}/error_codes.txt')
    logger: Logger = Logger(config)
    logger.log_system(logging.INFO, f'Set stage to {stage}')
    serial: SerialManagerAbstract = CreateSerialManager(config, logger, firmware_error_info)
    mqtt: MQTT = MQTT(config, logger)
    redis: Redis = Redis(0, config, logger)
    action_manager: ActionManager = ActionManager(serial, mqtt, redis, config, logger)

    action_manager.start_handling_instructions()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
