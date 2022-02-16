from typing import Any, Dict
import logging
from datetime import datetime
import json
import os

from common.config import Config


class LogEvent:
    def __init__(self, message: str, **kwargs: Any) -> None:
        self._dict: Dict[str, Any] = {'message': message, **kwargs}
        self._cached_item: Dict[str, Any] = {}

    def set_state(self, state: Dict[str, Any]) -> None:
        self._dict = state

    def get_state(self) -> Dict[str, Any]:
        return self._dict

    def add(self, **kwargs: Any) -> None:
        self._dict = {**self._dict, **kwargs}

    def add_to_cached_item(self, **kwargs: Any) -> None:
        self._cached_item = {**self._cached_item, **kwargs}

    def add_cached_item_to_key(self, key: str) -> None:
        if key in self._dict:
            self._dict[key].append(self._cached_item)
        else:
            self._dict[key] = [self._cached_item]
        self._cached_item = {}

    def send(self, level: int) -> None:
        logging.log(level, self)

    def __str__(self) -> str:
        return json.dumps(self._dict)


class Logger:
    def __init__(self, config: Config) -> None:

        if not os.path.exists('./logs'):
            os.makedirs('./logs')

        self._event_logger = logging.getLogger('robot.event')
        self._event_logger.setLevel(config.log_level_file)
        self._system_logger = logging.getLogger('robot.system')
        self._system_logger.setLevel(config.log_level_terminal)

        fh = logging.FileHandler(f'{config.root}/logs/robot.log')
        fh.setLevel(config.log_level_file)
        fh.setFormatter(logging.Formatter('%(message)s'))

        sh = logging.StreamHandler()
        sh.setLevel(config.log_level_file)
        sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%H:%M:%S'))

        self._event_logger.addHandler(fh)
        self._system_logger.addHandler(sh)

    # TODO: Create a util class and use it all over the code, see PM-1720
    def _get_utc_now(self):
        return datetime.utcnow()

    def create_event(self, message: str, **kwargs: Any) -> None:
        self._log_event = LogEvent(message,
                                   startTime=self._get_utc_now().isoformat(sep='T',
                                                                           timespec='milliseconds') + 'Z', **kwargs)

    def add_to_event(self, **kwargs: Any) -> None:
        self._log_event.add(**kwargs)

    def prepare_listitem_for_event(self, **kwargs: Any) -> None:
        self._log_event.add_to_cached_item(**kwargs)

    def add_listitem_to_event(self, key: str) -> None:
        self._log_event.add_cached_item_to_key(key)

    def send_event(self, level: int) -> None:
        self.add_to_event(level=logging.getLevelName(level),
                          endTime=self._get_utc_now().isoformat(sep='T', timespec='milliseconds') + 'Z')
        self._event_logger.log(level, self._log_event)

    def log_system(self, level: int, message: str) -> None:
        self._system_logger.log(level, message)

    def get_log_event_state(self) -> Dict[str, Any]:
        return self._log_event.get_state()

    def set_log_event_state(self, state: Dict[str, Any]) -> None:
        self._log_event.set_state(state)
