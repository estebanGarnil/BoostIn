# pubsub.py
import time
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
        
import json

def subscribe_to_channel_continu(channel_name):
    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    pubsub = client.pubsub()
    pubsub.subscribe(channel_name)

    while True:
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'].decode('utf-8'))
                        yield data
                        # Vérifiez si le message contient une condition d'arrêt
                        if data.get("etape") in ["arret", "echec"]:
                            logger.info("Message de fin reçu. Fermeture du générateur.")
                            return
                    except json.JSONDecodeError:
                        yield {"error": "Message reçu n'est pas un JSON valide"}
        except redis.ConnectionError as e:
            logger.error(f"Perte de connexion Redis : {e}. Reconnexion en cours...")
            time.sleep(1)  # Pause avant de réessayer
            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            pubsub = client.pubsub()
            pubsub.subscribe(channel_name)
        except Exception as e:
            logger.error(f"Erreur inconnue dans subscribe_to_channel_continu : {e}")
            break


def publish_message(channel, message):
    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    client.publish(channel, message)
