from __future__ import annotations
from typing import Any, Callable, Optional, Tuple
import json
import logging
import redis

from common.config import Config
from common.enums import State
from common.log_event import Logger
from common.types import Instruction, Command


class Redis:
    def __init__(self, db: int, config: Config, logger: Logger) -> None:
        self._logger: Logger = logger
        self._config: Config = config
        self._logger.log_system(logging.INFO, 'Init redis ...')
        self._redis: redis.Redis[Any] = redis.StrictRedis(db=db, decode_responses=True)

        if self._redis.ping():
            self._logger.log_system(logging.INFO, 'Successful init redis ...')
        else:
            self._logger.log_system(logging.CRITICAL, 'Something went wrong while init redis ...')
            exit(-2)

    def get_redis(self) -> redis.Redis[Any]:
        return self._redis

    def save(self) -> None:
        try:
            self._redis.save()
        except Exception:
            pass

    def set_position(self, x: int, y: int, z: int) -> None:
        self._redis.hmset('position', {'x': x, 'y': y, 'z': z})
        self.save()

    def del_position(self) -> None:
        self._redis.delete('position')
        self.save()

    def set_axis_position(self, axis: str, value: int) -> None:
        self._redis.hset('position', axis, value)
        self.save()

    def get_position(self) -> Optional[Tuple[int, int, int]]:
        if self._redis.exists('position'):
            position = self._redis.hgetall('position')
            return int(position['x']), int(position['y']), int(position['z'])
        else:
            return None

    def get_axis_position(self, axis: str) -> int:
        pos = self._redis.hget('position', axis)
        if pos is not None:
            return int(pos) if pos else 0
        else:
            self._logger.log_system(logging.CRITICAL, 'Missing Position. Can\'t determine Position!')
            self._logger.log_system(logging.CRITICAL,
                                    'Fatal error detected shutdown Bot script.\n\rHuman knowledge is needed.')
            exit(-5)

    def set_current_action(self, instruction: Instruction, command: Command) -> None:
        self._redis.hmset('action', {'instruction': json.dumps(instruction), 'command': json.dumps(command)})

    def get_current_action(self) -> Tuple[Instruction, Command]:
        action = self._redis.hgetall('action')
        if len(action) == 0:
            return None
        return (json.loads(action['instruction']), json.loads(action['command']))

    def set_initial_state(self) -> None:
        self._redis.set('state', State.IDLE.value, nx=True)
        self.save()

    def set_state(self, state: State) -> None:
        self._redis.set('state', state.value)
        self.save()

    def get_current_state(self) -> State:
        raw_state = self._redis.get('state')
        state = State(int(raw_state)) if raw_state else State.UNKNOWN
        return state

    def update_state(self, update_fun: Callable[..., State], *states: State) -> State:
        current_state = self.get_current_state()
        new_state = update_fun(current_state, *states)
        self.set_state(new_state)
        self.save()
        return new_state

    def get_log_item_state(self, logger: Logger) -> bool:
        log_item = self._redis.get('log_item')
        if log_item:
            logger.set_log_event_state(json.loads(log_item))

        return log_item is not None

    def set_log_item_state(self, logger: Logger) -> None:
        self._redis.set('log_item', json.dumps(logger.get_log_event_state()))
        self.save()
