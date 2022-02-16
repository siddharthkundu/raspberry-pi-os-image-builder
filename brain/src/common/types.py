from typing import Callable, Dict, Any

from common.enums import ErrorHandlerCode

Instruction = Dict[str, Any]
Command = Dict[str, Any]
Feedback = Dict[str, Any]

ErrorHandlerFactoryFunc = Callable[[ErrorHandlerCode], Callable[[Instruction, Command], None]]
