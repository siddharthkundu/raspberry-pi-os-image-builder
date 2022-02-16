from __future__ import annotations
from enum import Enum, IntFlag


class State(IntFlag):
    IDLE = 1
    HANDLING_INSTRUCTION = 2
    MOVING_X = 4
    MOVING_Y = 8
    MOVING_Z_UP = 16
    MOVING_Z_DOWN = 32
    HOMING_X = 64
    HOMING_Y = 128
    HOMING_Z = 256
    NON_SENSITIVE_ACTION = 512  # like weighting, taring, etc ... (no moving parts involved)
    TOGGLE_PUMPS_ON = 1024
    UNKNOWN = 2048

    @staticmethod
    def toggle_state(current_states: State, state: State) -> State:
        return current_states ^ state

    @staticmethod
    def remove_state(current_states: State, state: State) -> State:
        return current_states & ~state

    @staticmethod
    def remove_state_add_IDLE(current_states: State, state: State) -> State:
        return (current_states & ~state) | State.IDLE

    @staticmethod
    def add_state(current_states: State, state: State) -> State:
        return current_states | state

    @staticmethod
    def add_state_remove_IDLE(current_states: State, state: State) -> State:
        return (current_states | state) & ~State.IDLE

    @staticmethod
    def switch_states(current_states: State, to_remove: State, to_add: State) -> State:
        return State.add_state(State.remove_state(current_states, to_remove), to_add)

    @staticmethod
    def has_state(current_states: State, state: State) -> bool:
        return bool(current_states & state)

    @staticmethod
    def has_only_state(current_states: State, state: State) -> bool:
        return not bool((current_states ^ state) & ~state)


class InstructionType(Enum):
    SCAN_TO_ONBOARD = "SCAN_TO_ONBOARD"
    ONBOARD = "ONBOARD"


class CommandCode(Enum):
    ERROR = 5


class CommandSemantics(Enum):
    HOMING_X_POS = 1
    HOMING_Y_POS = 3
    HOMING_Z_POS = 5


class ErrorHandlerCode(Enum):
    FATAL_HOMING = 0
    FATAL_RECOVERY_HOMING = 1
    FATAL_MOVING = 2
    FATAL_RECOVERY_MOVING = 3
    FATAL_RECOVERY_PAUSE = 5
    FATAL_RECOVERY_SET_PUMPS = 7
    FATAL_SET_POS = 8
    STANDARD = 20
    RESET_Z = 21
    NOOP = 999
