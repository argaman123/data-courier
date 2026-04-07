import time
import queue
from threading import Thread
import pika
from pika.delivery_mode import DeliveryMode
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from src.common.config import logger, settings


class RabbitMQ(Thread):
    def __init__(self):
        super().__init__(name="RabbitMQ", daemon=True)
        self.enabled = settings.get("rabbitmq", {}).get("enabled", False)

        if self.enabled:
            self.host = settings.rabbitmq.host
            self.port = settings.rabbitmq.port
            self.exchange_name = settings.rabbitmq.get("exchange_name", "courier")
            self.routing_key_prefix = settings.rabbitmq.get("routing_key_prefix", "courier")
            self.reconnect_delay = settings.rabbitmq.get("reconnect_delay", 5)

            self.messages: queue.Queue[tuple[str, str]] = queue.Queue()


    def notify(self, folder: str, path: str):
        self.messages.put((folder, path))

    def run(self):
        while True:
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, port=self.port, heartbeat=60))
                channel = connection.channel()

                channel.exchange_declare(
                    exchange=self.exchange_name,
                    exchange_type='topic',
                    durable=True
                )
                logger.info(f"Successfully connected to RabbitMQ ({self.host}:{self.port})")

                while True:
                    folder, path = self.messages.get()
                    routing_key = f"{self.routing_key_prefix}.{folder}"

                    try:
                        channel.basic_publish(
                            exchange=self.exchange_name,
                            routing_key=routing_key,
                            body=path,
                            properties=pika.BasicProperties(delivery_mode=DeliveryMode.Persistent)
                        )
                        logger.info(f"Uploaded {path} to {routing_key}")

                    except (AMQPConnectionError, AMQPChannelError):
                        self.messages.put((folder, path))
                        break
            except AMQPConnectionError:
                logger.error(f"Connection failed to RabbitMQ ({self.host}:{self.port}), retrying in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)
            except pika.exceptions.AMQPError as e:
                logger.error(f"Unexpected error: {e}. Reconnecting in {self.reconnect_delay} seconds...")
                time.sleep(self.reconnect_delay)