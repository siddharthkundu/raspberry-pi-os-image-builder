import csv

from model.firmware_error import FirmwareError


class FirmwareErrorInfo:

    def __init__(self, errors_file: str) -> None:
        self.__look_up = {}
        with open(errors_file) as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                self.__look_up[int(row['Number'])] = FirmwareError(int(row['Number']), row['Task'], row['Description'])

    def get_error(self, error_id: int) -> FirmwareError:
        return self.__look_up.get(error_id, None)
