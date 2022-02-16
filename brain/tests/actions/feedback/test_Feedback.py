# type: ignore
import unittest
from unittest import mock
import random
import json

from actions.feedback.feedback_manager import FeedbackManager


@mock.patch('actions.memory')
@mock.patch('common.mqtt_client.MQTT')
@mock.patch('common.serial_manager.SerialManager')
@mock.patch('common.redis_client.Redis')
@mock.patch('common.config.Config')
@mock.patch('common.log_event.Logger')
class FeedbackTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.noop_factory = lambda _: lambda _1, _2: None

    @staticmethod
    def test_scan_to_onboard_successful_feedback(self, mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config,
                                                 mock_logger):
        layer_id = random.randint(1, 10)
        slot_id = random.randint(1, 10)
        farm_id = random.randint(1, 10)

        rfid = str(hex(random.randint(0, 255))).lstrip("0x") + ':' + str(hex(random.randint(0, 255))).lstrip("0x") \
            + ':' + str(hex(random.randint(0, 255))).lstrip("0x")
        mock_memory.current_rfid = rfid
        mock_config.stage = 'test'
        mock_config.farm_id = farm_id
        robot_id = random.randint(1, 10)
        mock_config.robot_id = robot_id
        feedback_manager = FeedbackManager(mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config, mock_logger)

        instruction = {'type': 'SCAN_TO_ONBOARD', 'layerId': layer_id, 'sourceSlotId': slot_id, 'farmId': farm_id}
        action = {'FAKE_ACTION': 'DONE'}

        feedback_manager.send_to_gateway(instruction, action, mock_memory, {})

        topic_name, payload_str = mock_mqtt.send.call_args[0]
        payload = json.loads(payload_str)
        assert topic_name == f'rc/test/farms/{farm_id}/robots/{robot_id}/feedback'

        assert payload["instructionStatus"] == 'SUCCESSFUL'
        assert payload["rfid"] == rfid
        assert payload["layerId"] == layer_id
        assert payload["slotId"] == slot_id

    @staticmethod
    def test_scan_to_onboard_failed_feedback(self, mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config,
                                             mock_logger):
        layer_id = random.randint(1, 10)
        slot_id = random.randint(1, 10)
        farm_id = random.randint(1, 10)

        mock_memory.current_rfid = 'invalid_rfid'
        mock_config.stage = 'test'
        mock_config.farm_id = farm_id
        robot_id = random.randint(1, 10)
        mock_config.robot_id = robot_id
        feedback_manager = FeedbackManager(mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config, mock_logger)

        instruction = {'type': 'SCAN_TO_ONBOARD', 'layerId': layer_id, 'sourceSlotId': slot_id, 'farmId': farm_id}
        action = {'FAKE_ACTION': 'DONE'}

        feedback_manager.send_to_gateway(instruction, action, mock_memory, {'statusCode': 400})

        topic_name, payload_str = mock_mqtt.send.call_args[0]
        payload = json.loads(payload_str)
        assert topic_name == f'rc/test/farms/{farm_id}/robots/{robot_id}/feedback'

        assert payload["instructionStatus"] == 'FAILED'
        assert payload["rfid"] == 'invalid_rfid'
        assert payload["layerId"] == layer_id
        assert payload["slotId"] == slot_id

    @staticmethod
    def test_onboard_failed_feedback(self, mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config, mock_logger):
        layer_id = random.randint(1, 10)
        slot_id = random.randint(1, 10)
        cell_id = '1T'
        gutter_id = 'te.st.0A.0B'

        mock_memory.current_rfid = 'invalid_rfid'
        mock_config.stage = 'test'
        farm_id = random.randint(1, 10)
        mock_config.farm_id = farm_id
        robot_id = random.randint(1, 10)
        mock_config.robot_id = robot_id
        feedback_manager = FeedbackManager(mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config, mock_logger)

        instruction = {'type': 'ONBOARD',
                       'gutterId': gutter_id,
                       'cellIdDestination': cell_id,
                       'layerIdDestination': layer_id,
                       'slotIdDestination': slot_id}
        action = {'FAKE_ACTION': 'DONE'}
        additional_details = {'statusCode': 'RFID != gutter_id',
                              'message': f"ONBOARD failed: expected- {gutter_id}, received- {mock_memory.current_rfid}"}

        feedback_manager.send_to_gateway(instruction, action, mock_memory, additional_details)

        topic_name, payload_str = mock_mqtt.send.call_args[0]
        payload = json.loads(payload_str)
        assert topic_name == f'rc/test/farms/{farm_id}/robots/{robot_id}/feedback'
        assert payload["layerId"] == layer_id
        assert payload["instructionStatus"] == 'FAILED'
        assert payload["statusCode"] == 'RFID != gutter_id'

    @staticmethod
    def test_successful_validation_feedback(self, mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config,
                                            mock_logger):
        layer_id = random.randint(1, 10)
        slot_id = random.randint(1, 10)
        farm_id = random.randint(1, 10)
        cell_id = 'T2'

        rfid = str(hex(random.randint(0, 255))).lstrip("0x") + ':' + str(hex(random.randint(0, 255))).lstrip(
            "0x") + ':' + str(hex(random.randint(0, 255))).lstrip("0x")
        mock_memory.current_rfid = rfid
        post_weight = random.randint(2001, 3000)
        mock_memory.post_weight = post_weight
        mock_config.stage = 'test'
        mock_config.farm_id = farm_id
        robot_id = random.randint(1, 10)
        mock_config.robot_id = robot_id
        feedback_manager = FeedbackManager(mock_memory, mock_mqtt, mock_serial, mock_redis, mock_config, mock_logger)

        instruction = {'type': 'VALIDATE', 'layerId': layer_id, 'slotId': slot_id, 'farmId': farm_id,
                       'cellId': cell_id}
        action = {'FAKE_ACTION': 'DONE'}

        feedback_manager.send_to_gateway(instruction, action, mock_memory, {})

        topic_name, payload_str = mock_mqtt.send.call_args[0]
        payload = json.loads(payload_str)
        assert topic_name == f'rc/test/farms/{farm_id}/robots/{robot_id}/feedback'
        assert payload["instructionStatus"] == 'SUCCESSFUL'
        assert payload["farmId"] == farm_id
        assert payload["cellId"] == cell_id
        assert payload["layerId"] == layer_id
        assert payload["slotId"] == slot_id
        assert payload["gutterId"] == rfid
        assert payload["weight"] == post_weight
