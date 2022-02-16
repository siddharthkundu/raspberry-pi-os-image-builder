import random
from threading import Lock
from typing import Any, Tuple, List, cast
from serial import Serial  # type: ignore
import glob
import time
import logging

from actions.feedback.firmware_error_info import FirmwareErrorInfo
from common.log_event import Logger
from common.config import Config
from common.enums import CommandCode
from model.firmware_error import FirmwareError
from util import strip_new_line


class SerialManagerAbstract:
    def send(self, message: List[int]) -> None:
        raise NotImplementedError("The method not implemented")

    def receive(self) -> Tuple[List[bytes], List[bytes]]:
        raise NotImplementedError("The method not implemented")

    def is_ok(self, left: List[bytes], right: List[bytes]) -> bool:
        raise NotImplementedError("The method not implemented")

    def get_firmware_error(self, left: List[bytes], right: List[bytes]) -> list[FirmwareError]:
        raise NotImplementedError("The method not implemented")


class SerialManagerMock(SerialManagerAbstract):
    def __init__(self, _: Config, logger: Logger) -> None:
        self.__lock = Lock()
        self._logger: Logger = logger
        self._detonate_count: int = 0

    def send(self, message: List[int]) -> None:
        self.__lock.acquire()
        self._logger.log_system(logging.INFO, f'Send message: {message}')
        self._logger.prepare_listitem_for_event(serial_in=str(message))
        self.__lock.release()

    def receive(self) -> Tuple[List[bytes], List[bytes]]:
        self.__lock.acquire()
        time.sleep(2)
        self._detonate_count += 1
        self._logger.log_system(logging.INFO, 'Received mocked message')

        self._logger.prepare_listitem_for_event(serial_out_right=str(self._detonate_count))
        self._logger.prepare_listitem_for_event(serial_out_left=str(self._detonate_count))
        self._logger.add_listitem_to_event('serial')

        if self._detonate_count != 10000:
            self.__lock.release()
            return (b'0 0 0 0 0 0 0 0 1'.split(b' '), b'0 0 30 0 0 0 0 0 1'.split(b' '))
        else:
            self.__lock.release()
            return (b'0 0 0 0 0 0 0 0 1'.split(b' '), b''.split(b' '))

    def is_ok(self, left: List[bytes], right: List[bytes]) -> bool:
        return not (left == [b''] or right == [b'']
                    or int(left[0]) == CommandCode.ERROR.value
                    or int(right[0]) == CommandCode.ERROR.value)

    def get_firmware_error(self, left: List[bytes], right: List[bytes]) -> list[FirmwareError]:
        if random() > .9:
            return [FirmwareError(random.randint(5000, 6999), "Fake Error", "Fake Error")]
        else:
            return None


class SerialManager(SerialManagerAbstract):
    def __init__(self, config: Config, logger: Logger, firmware_error_info: FirmwareErrorInfo) -> None:
        self.__lock = Lock()  # TODO: check if send and receive can be done concurrently
        self._logger: Logger = logger
        self.__firmware_error_info = firmware_error_info
        self._logger.log_system(logging.INFO, 'Start Init Serial Connections')

        self._ttys = glob.glob(config.serial_name_pattern)

        if len(self._ttys) < 2:
            self._logger.log_system(logging.CRITICAL, f'Only {len(self._ttys)} Serial Devices where found under '
                                                      f'{config.serial_name_pattern}')
            exit(1)

        self._right: Serial = Serial(self._ttys[0], 115200)
        self._left: Serial = Serial(self._ttys[1], 115200)

        time.sleep(2)

        # Fix left/right
        self._right.write(bytes([14]))  # type: ignore
        if cast(bytes, self._right.readline()).startswith(b'Side: Left version:'):  # type: ignore
            self._right, self._left = self._left, self._right  # type: ignore

        self._logger.log_system(logging.INFO, 'Successfully Init Serial Connections')

        self._NULL_ANSWER: List[bytes] = [b'0'] * 8

    def send(self, message: List[int]) -> None:
        with self.__lock:
            self._logger.log_system(logging.INFO, "Send to Serial: ")
            self._logger.log_system(logging.INFO, str(message))
            self._logger.prepare_listitem_for_event(serial_in=str(message))
            trys: int = 0
            while trys < 3:
                try:
                    self._right.write(bytes(message))  # type: ignore
                    break
                except Exception as e:
                    self._logger.log_system(logging.ERROR,
                                            f'Exception occurred on writing on the right USB, try number '
                                            f'{trys}: {e}')
                    trys += 1
            if trys >= 3:
                # Todo: Handle bad things
                return

            trys = 0
            while trys < 3:
                try:
                    self._left.write(bytes(message))  # type: ignore
                    break
                except Exception as e:
                    self._logger.log_system(logging.ERROR, f'Exception occurred on writing on the left USB, try number '
                                                           f'{trys}: {e}')
                    trys += 1
            if trys >= 3:
                # Todo: Handle bad things
                return

    def receive(self) -> Tuple[List[bytes], List[bytes]]:
        with self.__lock:
            left_answer = b''
            right_answer = b''
            trys: int = 0
            while trys < 3:
                try:
                    self._logger.log_system(logging.INFO, "Read right:")
                    right_answer = cast(bytes, self._right.readline())  # type: ignore
                    self._logger.log_system(logging.INFO, f"Read: {str(right_answer)}")
                    self._logger.prepare_listitem_for_event(serial_out_right=strip_new_line(str(right_answer)))
                    break
                except Exception as e:
                    self._logger.log_system(logging.ERROR,
                                            f'Exception occurred on reading on the right USB, try number '
                                            f'{trys}: {e}')
                    trys += 1

            trys = 0
            while trys < 3:
                try:
                    self._logger.log_system(logging.INFO, "Read left:")
                    left_answer = cast(bytes, self._left.readline())  # type: ignore
                    self._logger.log_system(logging.INFO, f"Read: {str(left_answer)}")
                    self._logger.prepare_listitem_for_event(serial_out_left=strip_new_line(str(left_answer)))
                    break
                except Exception as e:
                    self._logger.log_system(logging.ERROR, f'Exception occurred on reading on the left USB, try number '
                                                           f'{trys}: {e}')
                    trys += 1

            self._logger.add_listitem_to_event('serial')

            return (left_answer.split(b" "), right_answer.split(b" "))

    def is_integer(self, n: Any) -> bool:
        try:
            int(n)
            return True
        except ValueError:
            return False

    def is_ok(self, left: List[bytes], right: List[bytes]) -> bool:
        return not (left == [b''] or right == [b'']
                    or (self.is_integer(left[0]) and int(left[0]) == CommandCode.ERROR.value)
                    or (self.is_integer(right[0]) and int(right[0]) == CommandCode.ERROR.value))

    def __get_firmware_error(self, bytes: List[bytes]) -> FirmwareError:
        if (len(bytes) >= 3 and self.is_integer(bytes[0])
                and int(bytes[0]) == CommandCode.ERROR.value and self.is_integer(bytes[2])):

            error_id = int(bytes[2])
            return self.__firmware_error_info.get_error(error_id)

    def get_firmware_error(self, left: List[bytes], right: List[bytes]) -> list[FirmwareError]:
        result = []
        left_error = self.__get_firmware_error(left)
        if left_error is not None:
            result.append(left_error)
        right_error = self.__get_firmware_error(right)
        if right_error is not None:
            result.append(right_error)
        return result


def CreateSerialManager(config: Config, logger: Logger,
                        firmware_error_info: FirmwareErrorInfo) -> SerialManagerAbstract:
    if config.debug_only_serialless:
        return SerialManagerMock(config, logger)
    else:
        return SerialManager(config, logger, firmware_error_info)
