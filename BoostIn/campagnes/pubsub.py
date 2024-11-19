# pubsub.py
import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def subscribe_to_channel(channel_name):
    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    pubsub = client.pubsub()
    pubsub.subscribe(channel_name)

    for message in pubsub.listen():
        if message['type'] == 'message':
            return message['data']
        
def subscribe_to_channel_continu(channel_name):
    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    pubsub = client.pubsub()
    pubsub.subscribe(channel_name)
    logger.info(f"Abonné au canal : {channel_name}")

    # Retourne un générateur qui permet d'écouter en continu
    for message in pubsub.listen():
        if message['type'] == 'message':
            yield message['data']

def publish_message(channel, message):
    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    client.publish(channel, message)
