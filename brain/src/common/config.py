import logging
import os
import time
from typing import Dict

os.environ['TZ'] = 'Europe/Berlin'
time.tzset()


class Config:
    def __init__(self, root: str, filename: str, stage: str) -> None:
        print('Read Config ...')

        # Read Config-File
        # Maybe use a library for configs
        with open(f"{root}/{filename}", "r") as f:
            cfg: Dict[str, str] = {}
            for line in f:
                segments = line.split(" ")
                cfg[segments[0][:-1]] = segments[1]

        self.stage: str = stage
        self.robot_id: int = int(cfg["robot_id"].strip())
        self.farm_id: int = int(cfg["farm_id"].strip())
        self.root: str = root

        self.log_level_terminal: int = int(cfg.get("log_level_terminal", str(logging.DEBUG)).strip())
        self.log_level_file: int = int(cfg.get("log_level_file", str(logging.DEBUG)).strip())

        self.log_rollover_when: str = cfg.get("log_rollover_when", "midnight").strip()

        self.serial_name_pattern: str = cfg["serial_name_pattern"].strip()
        self.serial_timeout_right: int = int(cfg["serial_timeout_right"].strip())
        self.serial_timeout_left: int = int(cfg["serial_timeout_left"].strip())

        self.ignore_y_homing_error: bool = cfg.get("ignore_y_homing_error", "False").strip() == "True"

        self.min_weight_target_difference_before_watering: int = \
            int(cfg.get("min_weight_target_difference_before_watering", "60").strip())
        self.min_weight_target_difference_before_watering_full: int = \
            int(cfg.get("min_weight_target_difference_before_watering_full", "120").strip())
        self.min_weight_before_watering: int = int(cfg.get("min_weight_before_watering", "1000").strip())
        self.max_watering: int = int(cfg.get("max_watering", "350").strip())
        self.max_speed_watering: int = int(cfg.get("max_speed_watering", "80").strip())

        self.debug_only_serialless: bool = cfg.get("debug_only_serialless", "False").strip() == "True"
        self.disable_pump_weight_safety: bool = cfg.get("disable_pump_weight_safety", "False").strip() == "True"

        self.weight_offset: int = int(cfg.get("weight_offset", "0").strip())
        self.idle_time_sec: int = int(cfg.get("idle_time_sec", "600").strip())

        print('Config Summary:\n' + str(self.__dict__) + '\n-------------------')
