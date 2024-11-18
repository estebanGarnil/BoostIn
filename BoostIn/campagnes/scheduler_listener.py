import json
import time
import redis
from .services.LD import LDManager
from django_redis import get_redis_connection
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

def run_scheduler():
    while True:
        try:
            ld_manager = LDManager()
            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            pubsub = client.pubsub()
            pubsub.subscribe('request_channel')

            logger.info("En attente de messages sur le canal 'request_channel'...")

            for message in pubsub.listen():
                if message['type'] == 'message':
                    request_data = message['data'].decode('utf-8')
                    message_data = json.loads(request_data)
                    
                    process_response = process_message(ld_manager, message_data)
                    logger.info(f"run_scheduler.process_response = {process_response}")
                    
                    # Serialize the response before publishing
                    serialized_response = json.dumps(process_response)
                    client.publish('response_channel', serialized_response)
        except redis.ConnectionError as e:
            logger.info(f"run_scheduler -> Erreur de connexion Redis : {e}")
            time.sleep(5)
        except Exception as e:
            logger.info(f"run_scheduler -> Une erreur est survenue : {e}")
            time.sleep(5)


def process_message(ld_manager, message_data):
    try:
        action = message_data.get('action')
        object_id = message_data.get('object_id')
        
        if action == 'ADD':
            ld_manager.add(object_id)
            return {'etat': 'succes'}
        elif action == 'START':
            ld_manager.start(object_id)
            return {'etat': 'succes'}
        elif action == 'PROCHAINE_EXECUTION':
            pro = ld_manager.prochaine_execution(object_id)
            if pro is None:
                pro = "None"
            else:
                pro = pro.isoformat()
            return {'etat': 'succes', 'message': pro}
        elif action == 'ETAT_LANCEMENT':
            e = ld_manager.etat_lancement(object_id)
            if not e:
                ld_manager.stop(object_id)
            return {'etat': 'succes', 'message': str(e)}
        elif action == 'ADD_MANAGER':
            ld_manager.add_manager(object_id)
            return {'etat': 'succes'}
        elif action == 'STOP':
            ld_manager.stop(object_id)
            return {'etat': 'succes'}
        else: 
            return {'etat': 'succes', 'message': 'reponse envoyé'}
    except Exception as e:
        logger.info(f'process_message -> erreur : {e}')
        return {'etat': 'erreur', 'message': 'erreur renvoyé'}
