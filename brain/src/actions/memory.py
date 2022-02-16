from typing import Optional


class Memory:
    def __init__(self):
        self.custom_speed: Optional[int] = None
        self.pre_weight: int = 0
        self.post_weight: int = 0

        self.current_instruction_id: str = ''
        self.current_choice: int = 0

        self.current_rfid: str = ''

        self.pre_tank_level: int = 0
        self.post_tank_level: int = 0
