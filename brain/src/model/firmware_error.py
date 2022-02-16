from __future__ import annotations

from enum import unique, IntEnum
import json


@unique
class ErrorType(IntEnum):
    WARNING = 5
    ERROR = 6
    OK = 4


class FirmwareError:
    def __init__(self, number: int, task: str, description: str) -> None:
        self.number = number
        self.task = task
        self.description = description
        self.error_type = ErrorType(int(str(self.number)[0]))

    def __eq__(self, other) -> bool:
        """Overrides the default implementation"""
        if isinstance(other, FirmwareError):
            return self.number == other.number and self.task == other.task and self.description == other.description

        return NotImplemented

    def __ne__(self, other) -> bool:
        """Overrides the default implementation (unnecessary in Python 3)"""
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> str:
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.__dict__.items())))

    def __str__(self) -> str:
        return f'(number: {self.number}, task: {self.task}, description: {self.description}'

    def toJson(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__)

    @staticmethod
    def fromJson(json_str: str) -> FirmwareError:
        return json.loads(json_str, object_hook=lambda d: FirmwareError(d['number'], d['task'], d['description']))
