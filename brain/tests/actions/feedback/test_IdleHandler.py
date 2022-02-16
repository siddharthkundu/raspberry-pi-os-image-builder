import json
import logging
import string
import unittest
import random
from unittest.mock import patch

from actions.feedback.idle_handler import IdleHandler
from model.position import Position
from tests.util import get_random_alphanumeric
from util import Success, Failure


@patch('common.mqtt_client.MQTT')
@patch('common.log_event.Logger')
class IdleHandlerTest(unittest.TestCase):

    def test_given_a_current_action_in_redis_when_it_is_time_to_send_a_message_then_water_level_current_position_and_current_action_is_sent(self, mock_mqtt, mock_logger):

        stage = get_random_alphanumeric(5)
        farm_id = random.randint(1, 100)
        robot_id = random.randint(1, 100)
        water_level = random.randint(1, 100)
        x = random.randint(1, 100)
        y = random.randint(1, 100)
        z = random.randint(1, 100)
        idle_handler = IdleHandler(mock_mqtt, stage, farm_id, robot_id, mock_logger)
        current_action = ({
                              "expirationDateTime": "2022-01-12T16:13:41.763Z",
                              "instructionId": "",
                              "priority": "HIGH",
                              "startTime": "2022-01-12T13:13:43.729Z",
                              "type": "MANUAL"
                          },
                          {
                              "Destination": "rc/test/robots/6923/cmds",
                              "NeedsFeedbackOnSuccess": True,
                              "Str": "7 0 0 0 0 1 0 40",
                              "val": [
                                  "7",
                                  "0",
                                  "0",
                                  "0",
                                  "0",
                                  "1",
                                  "0",
                                  "1000"
                              ]
                          })

        expected_topic_name = f'rc/{stage}/farms/{farm_id}/robots/{robot_id}/idle'
        expected_payload = {
            'currentAction': [*current_action],
            'position': {
                'x': x,
                'y': y,
                'z': z
            },
            'waterLevel': water_level
        }
        expected_log_message_regex = f'Farm: {farm_id}, robot: {robot_id}, idle message:.*'

        idle_handler.send_message(current_action, Success(water_level), Success(Position(x, y, z)))
        self.assertEqual(farm_id, mock_logger.add_to_event.call_args_list[0][1]['idleFarmId'])
        self.assertEqual(robot_id, mock_logger.add_to_event.call_args_list[0][1]['idleRobotId'])
        self.assertEqual(expected_payload, json.loads(mock_logger.add_to_event.call_args_list[0][1]['idleMessage']))
        mock_logger.send_event.assert_called_once_with(logging.INFO)
        self.assertRegex( mock_logger.log_system.call_args.args[1], expected_log_message_regex)
        self.assertEqual(expected_topic_name, mock_mqtt.send.call_args.args[0])
        self.assertEqual(expected_payload, json.loads(mock_mqtt.send.call_args.args[1]))

    def test_given_a_current_action_in_redis_but_serial_communication_failing_when_it_is_time_to_send_a_message_then_no_message_is_sent(self, mock_mqtt, mock_logger):
        stage = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        farm_id = random.randint(1, 100)
        robot_id = random.randint(1, 100)
        water_level = random.randint(1, 100)
        x = random.randint(1, 100)
        y = random.randint(1, 100)
        z = random.randint(1, 100)
        idle_handler = IdleHandler(mock_mqtt, stage, farm_id, robot_id, mock_logger)
        current_action = ({
                              "expirationDateTime": "2022-01-12T16:13:41.763Z",
                              "instructionId": "",
                              "priority": "HIGH",
                              "startTime": "2022-01-12T13:13:43.729Z",
                              "type": "MANUAL"
                          },
                          {
                              "Destination": "rc/test/robots/6923/cmds",
                              "NeedsFeedbackOnSuccess": True,
                              "Str": "7 0 0 0 0 1 0 40",
                              "val": [
                                  "7",
                                  "0",
                                  "0",
                                  "0",
                                  "0",
                                  "1",
                                  "0",
                                  "1000"
                              ]
                          })



        idle_handler.send_message(current_action, Failure(RuntimeError('e')), Success(Position(x, y, z)))

        self.assertFalse(mock_logger.called)
        self.assertFalse(mock_mqtt.called)

        idle_handler.send_message(current_action, Success(water_level), Failure(RuntimeError('e')))

        self.assertFalse(mock_logger.called)
        self.assertFalse(mock_mqtt.called)

