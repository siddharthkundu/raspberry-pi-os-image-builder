from typing import Any, Callable, Dict, Tuple
from concurrent.futures import Future
import os
import threading
import re
import logging
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

from common.log_event import Logger
from common.config import Config


class MQTT:
    def __init__(self, config: Config, logger: Logger) -> None:
        self._logger: Logger = logger
        self._logger.log_system(logging.INFO, 'Start Init MQTT')

        path_to_client: str = f'{config.root}/client_{config.stage}/'

        self._endpoint: str = ''
        self._path_to_cert: str = ''
        self._path_to_key: str = ''
        self._path_to_root: str = ''
        self._client_id: str = ''

        with open(os.path.join(path_to_client, 'config.ini'), 'r') as c_file:
            c_lines = c_file.readlines()
            for line in c_lines:
                line_list = line.split(' ')
                if line_list[0] == 'IOT_ENDPOINT':
                    self._endpoint = line_list[2][:-1]
                if line_list[0] == 'CLIENT_ID':
                    if line_list[2][:-1] == '\n':
                        self._client_id = line_list[2][:-1]
                    else:
                        self._client_id = line_list[2]

        certs_path = os.path.join(path_to_client, 'certs')

        all_files = [f for f in os.listdir(certs_path) if os.path.isfile(os.path.join(certs_path, f))]
        self._path_to_cert = os.path.join(certs_path,
                                          [f for f in all_files if re.match(r'^(?!bootstrap).*\.pem\.crt$', f)][0])
        self._path_to_key = os.path.join(certs_path,
                                         [f for f in all_files if re.match(r'^(?!bootstrap).*\.pem\.key$', f)][0])
        self._path_to_root = os.path.join(certs_path,
                                          [f for f in all_files if re.match(r'^(?!bootstrap).*\.ca\.pem$', f)][0])

        for i in [(self._endpoint, 'ENDPOINT'),
                  (self._path_to_cert, 'PATH_TO_CERT'),
                  (self._path_to_key, 'PATH_TO_KEY'),
                  (self._path_to_root, 'PATH_TO_ROOT'),
                  (self._client_id, 'CLIENT_ID')]:

            if i[0] == '':
                self._logger.log_system(logging.ERROR, f"_____ No IoT {i[1]} found _____")

        # Spin up resources
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        self._mqtt_connection: mqtt.Connection = mqtt_connection_builder.mtls_from_path(  # type: ignore
            endpoint=self._endpoint,
            cert_filepath=self._path_to_cert,
            pri_key_filepath=self._path_to_key,
            client_bootstrap=client_bootstrap,
            ca_filepath=self._path_to_root,
            client_id=self._client_id)
        # Make the connect() call
        connect_future: Future[Dict[str, Any]] = self._mqtt_connection.connect()  # type: ignore
        # Future.result() waits until a result is available
        connect_future.result()
        self._logger.log_system(logging.INFO, f"Connected to {self._endpoint} with client ID '{self._client_id}'...")

    def subscribe(self, topic_name: str, callback: Callable[[str, str], None]) -> None:
        # Subscribe and listen to the messages
        mqtt_topic_subscribe_return: Tuple[Future[Dict[str, Any]], int] = self._mqtt_connection.subscribe(
            # type: ignore
            topic=topic_name,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=callback)

        # Wait for subscription to succeed
        mqtt_topic_subscribe_result = mqtt_topic_subscribe_return[0].result()
        self._logger.log_system(logging.INFO,
                                f"Subscribed to topic {topic_name} with {str(mqtt_topic_subscribe_result['qos'])}")

    def send(self, topic_name: str, data: str) -> None:
        def _send(topic_name: str, data: str):
            mqtt_topic_publish_return: Tuple[Future[Dict[str, Any]], int] = self._mqtt_connection.publish(
                # type: ignore
                topic=topic_name,
                payload=data,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            mqtt_topic_publish_return[0].result()

        threading.Thread(target=_send, args=[topic_name, data], daemon=True).start()
