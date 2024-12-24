import asyncio
from functools import wraps
import json
import random
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from django.conf import settings
from django.db import connection

from datetime import datetime, timedelta, timezone, date

import time as tm  # Utiliser un alias pour éviter les conflits
import redis
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import zoneinfo
import urllib.parse
from django.db.models import Q


from .navigateur import LinkedInNavigateur

import threading

from .Donnees import Etat, MessageObj, Prospect, EtatObj

from .email_envoyer import email_sender

from ..models import NomChamp, Prospects, TachesProgrammes, Con, Erreur, ValeurChamp, codeerreur, Message, Manager, Statutes, StatistiquesCampagne

from .trace import trace_function_log

lock = threading.Lock()

email = email_sender()

import logging

from multiprocessing import Process
import os 

logger = logging.getLogger(__name__)

from functools import wraps
import logging

logger = logging.getLogger(__name__)

def check_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from django.db import connections, close_old_connections

            # Ferme les anciennes connexions
            close_old_connections()

            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT DATABASE();")
                    logger.info(cursor.fetchone())
            except Exception as e:
                logger.info(f"Erreur de connexion : {e}")

            # Récupère la connexion par défaut
            connection_to_use = connections['default']

            # Vérifie si la connexion est utilisable
            if not connection_to_use or not connection_to_use.is_usable():
                try:
                    connection_to_use.close()  # Ferme l'ancienne connexion
                    connection_to_use.connect()  # Réinitialise la connexion
                    logger.info("Connexion MySQL rétablie avec succès.")
                except Exception as e:
                    logger.error(f"Échec de la reconnexion MySQL : {e}")
                    raise e

            # Exécute la fonction décorée
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erreur dans la fonction '{func.__name__}': {e}")
            raise
    return wrapper


class LDManager:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LDManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.objets = {}
            cls._instance.taches = BackgroundScheduler() 
            cls._instance.existing_times = set()

            DATABASE_URL = f"mysql+pymysql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD']}@" \
                   f"{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}"

            cls._instance.taches.add_jobstore('sqlalchemy', url=DATABASE_URL)

            cls._instance.taches.start()
            manage = Manager.objects.all()
            for m in manage:
                cls._instance.objets[str(m.idcon.id)] = LDCon(m.idcon.id)

        return cls._instance         
    
    @staticmethod
    def suppression_campagne(_id):
        def suppression(_id):
            try:
                con = Con.objects.get(id=_id)

                # Suppression des messages
                messages = Message.objects.filter(idcon=con)
                for m in messages:
                    m.delete()
                    logger.info(f"Message {m} deleted")

                # Suppression des champs et valeurs associées
                nchamp = NomChamp.objects.filter(idcon=con)
                vchamp = ValeurChamp.objects.filter(id_champ__in=nchamp)
                vchamp.delete()
                logger.info("Valeurs de champs supprimées")
                nchamp.delete()
                logger.info("Noms de champs supprimés")

                # Suppression des prospects et statuts
                prospects = Prospects.objects.filter(idcon=con)
                for p in prospects:
                    status = p.statutes
                    p.delete()
                    status.delete()
                    logger.info("Prospect supprimé avec statut")

                # Suppression de la campagne
                con.delete()
                logger.info("Campagne supprimée")
            except Exception as e:
                logger.error(f"Erreur durant la suppression : {e}")

        try:
            process = Process(target=suppression, args=(_id,))
            process.start()
            process.join()  # Attendre la fin du processus pour synchronisation
            
            return True
        except Exception as e:
            logger.error(f"Erreur durant le démarrage du processus : {e}")
            return False
    
    def ajouter_tache_10_seconde(self, _id):
        now = datetime.now()

        # Ajouter 15 secondes à l'heure actuelle
        exec_time = now + timedelta(seconds=10)

        trigger = DateTrigger(run_date=exec_time)
        self.taches.add_job(
            LDManager._execute_task,
            trigger,
            id=f"{_id}_{exec_time}",
            replace_existing=True,
            args=[str(_id)]
        )

        # Log de l'heure d'exécution
        logger.info(f"Tâche ajoutée pour l'ID {_id}. Heure d'exécution prévue : {exec_time}")

    @trace_function_log
    def attribution_horaire(self, h1 : int, h2 : int, j1:str, j2:str, _id : str, nb_exec : int=None):
        """
        _id[0] == 'C' : correspond a LDC -> manager
        _id[1:4] == 'CON' : correspond a LDCon -> conexion
        """
        if nb_exec is None:
            nb_exec = 20

        if self.existing_times is None:
            self.existing_times = set()

        JOUR = {'1': 'mon', '2': 'tue', '3': 'wed', '4': 'thu', '5': 'fri', '6': 'sat', '7': 'sun'}
        days = [JOUR[str(i)] for i in range(int(j1), int(j2) + 1)]
        day = JOUR[j1]+'-'+JOUR[j2]
        logger.info(f"jour : {day}")

        if _id[0] == 'C':            
            start_time = datetime.now().replace(hour=h1, minute=0, second=0, microsecond=0)
            end_time = datetime.now().replace(hour=h2, minute=0, second=0, microsecond=0)

            task_duration = timedelta(minutes=4)  # Durée de chaque tâche
            existing_tasks = self.get_existing_tasks(task_duration)
            
            time_slots = self.generate_non_overlapping_times(start_time, end_time, nb_exec, task_duration, existing_tasks)
            
            for exec_time in time_slots:
                if exec_time.strftime('%a').lower() in days:
                    trigger = DateTrigger(run_date=exec_time)
                    self.taches.add_job(
                        LDManager._execute_task,
                        trigger,
                        id=f"{_id}_{exec_time}",
                        replace_existing=True,
                        args=[str(_id)]
                    )

        elif _id[1:4] == 'CON':
            logger.info(f"heure d'execution : {h1+1}")
            trigger = CronTrigger(
                hour=h1+1, 
                minute=0, 
                day_of_week=day
                )
            self.taches.add_job(LDManager._execute_task, trigger=trigger, replace_existing=True, id=_id, args=[str(_id)])

    def make_timezone_aware(self, dt):
        from pytz import utc
        """
        Convertit un datetime offset-naive en offset-aware avec le fuseau horaire UTC.
        Si le datetime est déjà aware, il est retourné tel quel.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=utc)
        return dt
    
    def get_existing_tasks(self, task_duration):
        """
        Récupère les plages horaires existantes des tâches dans le scheduler.

        :param task_duration: Durée de chaque tâche (timedelta)
        :return: Liste des plages horaires existantes [(start, end), ...]
        """
        existing_tasks = []
        for job in self.taches.get_jobs():
            if job.next_run_time:  # Vérifie si une prochaine exécution est programmée
                start_time = self.make_timezone_aware(job.next_run_time)  # Rendre timezone-aware
                end_time = start_time + task_duration
                existing_tasks.append((start_time, end_time))
        return existing_tasks

    @trace_function_log
    def generate_non_overlapping_times(self, start_time, end_time, nb_exec, task_duration, existing_tasks):
        """
        Génère des heures aléatoires pour des tâches en respectant un écart minimum
        et en évitant les chevauchements avec des tâches existantes.
        
        :param start_time: Heure de début de la plage horaire
        :param end_time: Heure de fin de la plage horaire
        :param nb_exec: Nombre de tâches à planifier
        :param task_duration: Durée de chaque tâche (timedelta)
        :param existing_tasks: Liste des plages horaires des tâches existantes [(start, end), ...]
        :return: Liste des heures de début des tâches planifiées
        """
        time_slots = []
        attempts = 0
        max_attempts = nb_exec * 50  # Éviter les boucles infinies
        min_gap = 5  # Écart minimal en minutes
        current_time = self.make_timezone_aware(datetime.now())
        no_task_zone_end = current_time + timedelta(minutes=10)  # Plage où aucune tâche ne peut être planifiée
        
        # Normaliser start_time et end_time
        start_time = self.make_timezone_aware(start_time)
        end_time = self.make_timezone_aware(end_time)

        while len(time_slots) < nb_exec and attempts < max_attempts:
            # Générer un décalage en minutes dans l'intervalle
            random_minutes = random.randint(0, int((end_time - start_time).total_seconds() // 60))
            exec_time_start = start_time + timedelta(minutes=random_minutes)
            exec_time_start = self.make_timezone_aware(exec_time_start)  # Normaliser
            exec_time_end = exec_time_start + task_duration

            # Vérification de non-chevauchement avec les plages existantes
            overlaps_existing = any(
                (exec_time_start < existing_end and exec_time_end > existing_start)
                for existing_start, existing_end in existing_tasks
            )

            # Vérification de non-chevauchement avec les nouvelles plages générées
            overlaps_generated = any(
                abs((exec_time_start - generated_time).total_seconds()) < min_gap * 60
                for generated_time in self.existing_times
            )

            # Empêcher la planification d'une tâche dans la plage des 10 prochaines minutes à partir de l'heure actuelle
            in_no_task_zone = current_time <= exec_time_start < no_task_zone_end

            if not overlaps_existing and not overlaps_generated and not in_no_task_zone:
                logger.info(f"Heure aléatoire générée : {exec_time_start}")
                time_slots.append(exec_time_start)
                self.existing_times.add(exec_time_start)
                existing_tasks.append((exec_time_start, exec_time_end))  # Ajouter la tâche à la liste existante
            else:
                logger.debug(f"Conflit détecté pour l'heure {exec_time_start}, tentative ignorée.")
            
            attempts += 1

        logger.info(f"Nombre d'horaires générés dans la journée : {len(time_slots)}")
        if len(time_slots) < nb_exec:
            logger.warning("Impossible de planifier toutes les tâches sans chevauchement.")

        return time_slots

    @trace_function_log
    @staticmethod
    def _execute_task(_id):
        logger = logging.getLogger(__name__)
        logger.info(f"id : {_id}, {_id[0:4]}")
        logger.info("Lancement de la methode _execute_task")
        m = LDManager()
        if _id[0] == 'C':

            logger.info("lancement de ldc")
            logger.info(f'pid du lancement : {os.getpid}')
            _id = _id[-2:]
            LDconector = LDCon(_id) ## creer une nouvelle instance

            LDconnexion = LDconector.get_connexion()
            logger.info("get_connexion")
            LDconnexion.demander_connexion()
            logger.info("demander connexion")
            # ldc = m.objets[_id].get_connexion()

            # async
            # logger.info("dans un processus separé")
            # process = Process(target=ldc.demander_connexion)
            # process.start()

        elif _id[0:4] == '1CON':
            _id = _id[-2:]
            m.start(_id, exe=True)
            
        elif _id[0:2] == '2CON':
            logger.info('execution du programme de fin de journée')
            _id = _id[-2:]
            m.objets[_id].start_observer()

        else:
            logger.info("rien")

    @trace_function_log
    def prochaine_execution(self, _id : str) -> datetime:
        matching_tasks = []
        for job in self.taches.get_jobs():
            if _id in str(job.id) :
                matching_tasks.append(job.next_run_time)
        logger.info(f"heures trouvées : {matching_tasks}")
        heures_triees = sorted(matching_tasks)
        logger.info(f"heure triés : {heures_triees}")
        paris_tz = zoneinfo.ZoneInfo("Europe/Paris")
        for d in heures_triees:
            if datetime.now(paris_tz) < d:
                return d
        return None

    @trace_function_log
    def add(self, _id, _canal : str) -> None:
        self.objets[_id] = LDCon(ID=_id, canal=_canal)

    @trace_function_log
    def start(self, id, exe=True) -> None:
        self.objets[id].start_programmer_tache()
        self.objets[id].start(exe)

    @trace_function_log
    def start_demarage(self) -> None:
        for _id in self.objets.keys():
            self.start(_id)

    def test_message(self, _id):
        obj = LDCon(ID=_id, canal="canal")
        ldm = obj.get_message()
        ldm.start()

    @trace_function_log
    @check_connection
    def stop(self, _id) -> None:
        prefix = 'C'+_id
        jobs = self.taches.get_jobs()

        # Identifier et supprimer les tâches correspondant au préfixe
        for job in jobs:
            if job.id.startswith(prefix):
                logger.info(f'Suppression de la tâche : {job.id}')
                self.taches.remove_job(job.id)

        # Suppression des objets liés
        if prefix[1:] in self.objets:
            self.objets[prefix[1:]].stop()
            del self.objets[prefix[1:]]

        job = self.taches.get_job('1CON'+str(_id))
        logger.info(f'job supression 1CON : {job}')
        if job:
            self.taches.remove_job('1CON'+str(_id))
        job = self.taches.get_job('2CON'+str(_id))
        if job:
            self.taches.remove_job('2CON'+str(_id))
        try:
            con = Con.objects.get(id=_id)
            manager = Manager.objects.get(idcon=con)
            manager.delete()
        except Exception as e:
            logger.info(e)

        self.objets[str(_id)].stop()
        del self.objets[str(_id)]

    @trace_function_log
    def etat_lancement(self, id) -> None:
        return self.objets[id].lancement_reussi()
    
    @trace_function_log
    @check_connection
    def add_manager(self, _id) -> None:
        con = Con.objects.get(id=_id)
        if Manager.objects.filter(idcon=con).count() <= 0:
            m = Manager(idcon=con)
            m.save()      

    def connexion_linkedin(self, _id, utilisateur, mdp):
        logger.info("connexion_linkedin_part1")
        self.objets[_id].connexion_linkedin(utilisateur, mdp)
        logger.info("connexion_linkedin_part1 fini")

class LDCon:
    """
    Gestionnaire des objets LDC, LDM et LDObserver.

    La classe `LDCon` est responsable de la gestion des composants `LDC` (connexion), `LDM` (message), et `LDObserver` (observateur).
    Elle interagit avec une base de données via l'objet `LDDB` pour récupérer les informations nécessaires telles que le token de connexion et l'adresse e-mail.
    Elle gère également le démarrage, l'arrêt, la planification et la prochaine exécution de ces composants.

    Attributs:
        ID (int): L'identifiant unique de l'objet.
        email (str): L'adresse e-mail associée à l'objet.
        __token_ld (str): Le token de connexion récupéré depuis la base de données.
        __navigateur (LinkedInNavigateur): Navigateur LinkedIn initialisé avec le token de connexion.
        started (bool): Indique si les composants de l'objet sont démarrés.
        etat (Etat): L'état actuel de l'objet.
        message_erreur (str): Le message d'erreur associé à l'objet, s'il y en a un.

    Méthodes:
        __recuperer_token(): Récupère le token de connexion depuis la base de données.
        start(): Démarre les composants de l'objet si l'heure actuelle est dans la plage d'activité définie.
        stop(): Arrête et supprime les composants actifs de l'objet.
        programmer_lancement(): Programme le démarrage et l'arrêt automatique de l'objet à des heures spécifiques.
        prochaine_execution(): Renvoie la date et l'heure de la prochaine exécution prévue pour l'objet.
    """
    def __init__(self, ID : int, canal : str = "") -> None:
        self.ID : int = ID
        # self.__token_ld : str = self.__recuperer_token()
        self.__navigateur : LinkedInNavigateur = LinkedInNavigateur(f"session{self.ID}", canal)
        self.__canal : str = canal

        self.__connexion : LDC = LDC(self, self.__navigateur, self.__canal)
        self.__observer : LDObserver = LDObserver(self, self.__navigateur, self.__canal)
        self.__message : LDM = LDM(self, self.__navigateur, self.__canal)
        
        self.etat = None
    
    def connexion_linkedin(self, utilisateur, mdp):
        try:
            logger.info("debut")
            asyncio.run(self.__navigateur.login_execution(utilisateur, mdp, "https://www.linkedin.com/"))
            logger.info(f"fin de l'execution connexion_linkedin")
            return True
        except Exception as e: 
            logger.info(f"erreur lors de l'exec : {e}")
            return False


    @trace_function_log
    @check_connection
    def __recuperer_token(self) -> str:
        logger.info("execution de recuperer _token")
        c = Con.objects.get(id=self.ID)
        return str(c.token)
    
    @trace_function_log
    def get_connexion(self):
        return self.__connexion
    
    @trace_function_log
    def get_message(self):
        return self.__message
    
    @trace_function_log
    @check_connection
    def start_programmer_tache(self):
        c = Con.objects.get(id=self.ID)
        m = LDManager()
        m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='1CON'+str(c.id))
        m.attribution_horaire(h1=int(c.heureactivite[3:5]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='2CON'+str(c.id))
    @trace_function_log
    def start(self, exe=True):
        logger.info(f"demarage du multiprocessus {os.getpid()}")
        c = self.__connexion.start()
        if exe:
            processA = Process(target=self.run_process)
            processA.start()
    @trace_function_log
    def start_observer(self):
        self.__observer.start()
        
    def run_process(self):
        logger.info(f"demarage du multiprocessus {os.getpid()}")
        tm.sleep(4)
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description" : f"Attribution des horaires d'execution reussi",
            "etape":"suivant"
        }
        client.publish(self.__canal, json.dumps(data))
        logger.info(f"message envoyé : {data}")

        a = self.__observer.start()
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Analyse des nouvelles connexions reussi",
            "etape": "suivant"
        }
        client.publish(self.__canal, json.dumps(data))
        logger.info(f"message envoye : {data}")

        b = self.__message.start()
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Envoi des messages reussi",
            "etape": "suivant"
        }
        client.publish(self.__canal, json.dumps(data))
        logger.info(f"message envoyé : {data}")

        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Fin de la sequence lancement : reussi",
            "etape": "suivant"
        }
        client.publish(self.__canal, json.dumps(data))
        logger.info(f"message envoyé : {data}")

        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Fin de la sequence de lancement",
            "etape": "arret"
        }
        client.publish(self.__canal, json.dumps(data))
        logger.info(f"message envoyé : {data}")

    @trace_function_log
    def lancement_reussi(self) -> bool:
        return self.__observer.lancement_valide
    @trace_function_log
    def stop(self):
        del self.__connexion
        del self.__observer
        del self.__message
    
    @trace_function_log
    def majStatistiques(self):
        try:
            con = Con.objects.get(id=self.ID)
            not_sent = Prospects.objects.filter(idcon=con, statutes__statutes='Not sent').count()
            on_hold = Prospects.objects.filter(idcon=con, statutes__statutes='On hold').count()
            accepted = Prospects.objects.filter(idcon=con, statutes__statutes='Accepted').count()
            message1 = Prospects.objects.filter(idcon=con, statutes__statutes='1ST').count()
            message2 = Prospects.objects.filter(idcon=con, statutes__statutes='2ND').count()
            message3 = Prospects.objects.filter(idcon=con, statutes__statutes='3RD').count()
            success = Prospects.objects.filter(idcon=con, statutes__statutes='Success').count()
            refused = Prospects.objects.filter(idcon=con, statutes__statutes='Refused').count()

            accepted += message1+message2+message3

            statistiques = StatistiquesCampagne.objects.update_or_create(
                idcon=con, 
                date= date.today(), 
                defaults={
                    'not_sent': not_sent,
                    'on_hold': on_hold,
                    'accepted': accepted,
                    'success': success,
                    'refused': refused,
                    'message1st': message1,
                    'message2nd': message2,
                    'message3rd': message3
                }
            )
        except Exception as e:
            logger.info(f"erreur : {e}")

class LDC:
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur, canal : str) -> None:
        self.con : LDCon = user  # l'id de con dans la base de donnée
        self.__navigateur : LinkedInNavigateur = navigateur ## le navigateur pour pouvoir lancer des instance de chrome
        self.__CpJ : int = 20 ## connexion par jour
        self.lancement_valide = None
        self.__canal = canal

        self.etat = EtatObj.STOP

    def check_prospect_restants(self):
        statuts_matching = Statutes.objects.filter(statutes__icontains="Not sent")

        if statuts_matching.exists():
            # Compter le nombre de prospects associés à ces statuts
            count = Prospects.objects.filter(statutes__in=statuts_matching, idcon=self.con.ID).count()
            logger.info(f"Nombre de prospects avec un statut contenant 'Not sent' : {count}")
            return count > 0
        else:
            logger.info("Aucun statut correspondant à 'Not sent' n'a été trouvé.")
            return None


    @trace_function_log
    def start(self) -> None:
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Attribution des horaires de connexion",
            "etape": "en_cours"
        }
        client.publish(self.__canal, json.dumps(data))
        self.__programmer_envoi()
        self.etat = EtatObj.RUNNING

    @trace_function_log
    @check_connection
    def __programmer_envoi(self) -> None:
        """
        Programme l'envoi des tâches pour chaque prospect.
        """
        if self.check_prospect_restants():
            c = Con.objects.get(id=self.con.ID)
            m = LDManager()
            m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], nb_exec=self.__CpJ, _id='C'+str(c.id))
   
    @trace_function_log
    @check_connection
    def demander_connexion(self) -> None:
        logger.info("lancement de la demande de connexion")

        if self.check_prospect_restants():

            p = Prospects.objects.filter(idcon__id=self.con.ID, statutes__statutes=Etat.NOT_SENT.value).first()
            if self.__navigateur.start(p.linkedin_profile):
                ## cas de base -> le prospect à été ajouté
                etat : Etat = self.__navigateur.connexion()
                if etat is not None or etat is not Etat.FAILURE:
                    logger.info(f"mise a jour du prospect avec la valeur : {etat.value}")
                    p.statutes.statutes = etat.value
                    p.statutes.save()
                    dernier_nom = self.__navigateur.dernier_nom
                    if dernier_nom is not None:
                        p.complete_name = dernier_nom
                    self.__navigateur.close()
            else : 
                c = Con.objects.get(id=self.con.ID)
                codeerr = codeerreur.objects.get(id=2)
                if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
                    e = Erreur(
                        idcon = c,
                        etat = False,
                        date_err = datetime.now(),
                        code_err = codeerr
                    )
                    e.save()

            logger.info("c'est fini")

class LDM:
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur, canal : str):
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur

        self.__taches : BackgroundScheduler = BackgroundScheduler()
        self.__prospect : Prospect = []
        self.__message : MessageObj = []
        self.__canal = canal

    @trace_function_log
    def start(self) -> None:
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Demarage de l'envoi des message du jour",
            "etape": "en_cours"
        }
        client.publish(self.__canal, json.dumps(data))

        self.__recuperer_message()
        self.__recuperer_prospect()

        self.__envoyer_message()

    @trace_function_log
    @check_connection
    def __recuperer_message(self) -> None:
        """
        Récupère les messages associés à l'utilisateur depuis la base de données et initialise les objets `Message`.
        """
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Recuperation des messages",
            "etape": "en_cours"
        }
        client.publish(self.__canal, json.dumps(data))
        con = Con.objects.get(id=self.con.ID)

        message = Message.objects.filter(idcon=con).values('id', 'corp', 'idfonc__tempsprochaineexec', 'idfonc__statutes_activation', 'idfonc__type')
        i = 0
        for m in message:
            logger.info(f'message : {m}')
            self.__message.append(MessageObj(m['id'], m['corp'], m['idfonc__tempsprochaineexec'], Etat(m['idfonc__statutes_activation'])))
            i+=1
        logger.info(f'message : {self.__message}')

    @trace_function_log
    @check_connection
    def __recuperer_prospect(self) -> None:
        """
        Ajoute les prospects à traiter pour chaque message.
        """
        try:
            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            data = {
                "description": f"Recuperation des prospects",
                "etape": "en_cours"
            }
            client.publish(self.__canal, json.dumps(data))
            con = Con.objects.get(id=self.con.ID)

            for m in self.__message:
                t = (datetime.now() - timedelta(days=m.jour)).date()
                logger.info(f'm.jour = {m.jour}, timezone.now() - timedelta(days=m.jour) = {str(t)}')

                prospect = Prospects.objects.filter(
                    idcon=con,
                    statutes__statutes=m.statut.value,
                    statutes__changedate__lte=(datetime.now() - timedelta(days=m.jour)).date()
                    ).values('id', 'name', 'linkedin_profile')
                logger.info(f'prospect : {prospect}')
                for p in prospect:
                    corp = m.corp

                    var = re.findall(r'#(.*?)#', corp)
                    logger.info(f'var : {var}')

                    for v in var:
                        variable = NomChamp.objects.get(idcon=con, nom=v)
                        pr = Prospects.objects.get(id=p["id"])

                        val = ValeurChamp.objects.get(id_prospect=pr, id_champ=variable)

                        logger.info(f"val : {val.valeur}, v : {v}, replace #{v}#, {val.valeur}")

                        corp = corp.replace(f'#{v}#', val.valeur)
            
                    m.prospect.append(Prospect(p["id"], p["name"], p["linkedin_profile"], corp))
            logger.info(f'message : {self.__message}')
        except Exception as e:
            logger.info(f'erreur dans __recuperer_prospect : {e}')

    @trace_function_log
    @check_connection
    def __envoyer_message(self):
        """
        Envoie les messages prévus à tous les prospects dans la liste pour chaque instance de message.

        Cette méthode effectue les actions suivantes :
        2. Si le navigateur est démarré avec succès, la méthode parcourt chaque message dans `self.__message`, et pour chaque prospect dans la liste du message :
            - Accède à la page LinkedIn du prospect.
            - Envoie le message personnalisé au prospect.
            - Met à jour le statut du prospect dans la base de données en fonction du résultat de l'envoi (`Etat.SENT` ou `Etat.SUCCESS`).
            - Attend un délai aléatoire entre 1 et 5 secondes avant de passer au prochain prospect.
        3. Ferme le navigateur après l'envoi des messages.
        4. Si le démarrage du navigateur échoue, met à jour l'état de l'utilisateur à `Etat.FAILURE`, enregistre un message d'erreur, et envoie un email à l'utilisateur pour notifier la nécessité de mettre à jour son token de connexion.

        Returns:
            None
        """

        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Envoi des messages",
            "etape": "en_cours"
        }
        client.publish(self.__canal, json.dumps(data))

        c = Con.objects.get(id=self.con.ID)
        codeerr = codeerreur.objects.get(id=2)
        if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
            cpt = len([1 for m in self.__message if len(m.prospect) > 0])
            if cpt == 0:
                return None
            if self.__navigateur.start(c.linkedin_lien):
                for m in self.__message:
                    logger.info(f'nombre de prospects : {len(m.prospect)}')
                    for p in m.prospect:
                        tm.sleep(3)
                        logger.info(f"p -> : {p}")
                        self.__navigateur.get(p.lien)
                        envoi = self.__navigateur.envoiMessage(p.corp)

                        if envoi == Etat.SENT:
                            logger.info("maj du prospect")
                            prospect = Prospects.objects.get(id=p.ID)
                            statute = prospect.statutes
                            statute.statutes = m.statut.suivant().value
                            statute.save()

                        if envoi == Etat.SUCCESS:
                            logger.info("maj du prospect")
                            prospect = Prospects.objects.get(id=p.ID)
                            statute = prospect.statutes
                            statute.statutes = Etat.SUCCESS.value
                            statute.save()

                        tm.sleep(random.randint(1,3))
                tm.sleep(5)
                self.__navigateur.close()
            else : 
                c = Con.objects.get(id=self.con.ID)
                codeerr = codeerreur.objects.get(id=2)
                if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
                    e = Erreur(
                        idcon = c,
                        etat = False,
                        date_err = datetime.now(),
                        code_err = codeerr
                    )
                    e.save()

class LDObserver:
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur, canal : str) -> None:
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur
        self.lancement_valide = None
        self.__canal = canal

    @trace_function_log
    def start(self) -> None:        
        tm.sleep(2)
        client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        data = {
            "description": f"Demarage de l'analyse des nouvelles connexions",
            "etape": "en_cours"
        }
        client.publish(self.__canal, json.dumps(data))

        self.__update_statute_accepted()

        self.con.majStatistiques()

    @trace_function_log
    @check_connection
    def __update_statute_accepted(self) -> None:
        """
        Met à jour le statut de chaque prospect.

        Cette méthode met à jour le statut des prospects pour indiquer qu'ils ont accepté la connexion. Après une attente de 5 secondes, 
        elle vérifie que l'utilisateur n'est pas en état d'échec (`Etat.FAILURE`). Si ce n'est pas le cas, elle verrouille les ressources partagées, 
        appelle la méthode `__comparer_statute()` pour obtenir la liste des prospects concernés, puis met à jour le statut de chaque prospect 

        Returns:
            None
        """
        try:    
            tm.sleep(5)
            c = Con.objects.get(id=self.con.ID)
            is_erreur = Erreur.objects.filter(idcon=c, etat=0, code_err=codeerreur.objects.get(id=1)).count() != 0
            logger.info(f'__update_statute_accepted -> nb erreur : {is_erreur}')
            if not is_erreur:  
                logger.info("__update_statute_accepted -> pas d'erreur")  
                l = self.__comparer_statute()
                l_success = l[1]
                l = l[0]
                logger.info(f'prospects a ajouter : {l}')
                if self.lancement_valide != False:
                    logger.info(f"__update_statute_accepted l -> {l}")
                    for e in l:
                        logger.info(f'__update_statute_accepted -> {e}')
                        prospect = Prospects.objects.get(id=e)
                        statute = prospect.statutes
                        logger.info(f'LDObserver.__update_statute_accepted -> {statute.statutes}')
                        logger.info(f'Etat.SENT.value : {Etat.SENT.value} | Etat.ON_HOLD : {Etat.ON_HOLD.value}')
                        if statute.statutes.upper() == Etat.ON_HOLD.value.upper() or statute.statutes.upper() == Etat.NOT_SENT.value.upper():
                            logger.info(f"Maj du prospect {statute.statutes} -> {Etat.ACCEPTED.value} ")
                            statute.statutes = Etat.ACCEPTED.value
                            statute.changedate = datetime.now().date()

                            statute.save()
                    logger.info(f"__update_statute_accepted -> _success : {l_success}")
                    for e in l_success:
                        prospect = Prospects.objects.get(id=e)
                        statute = prospect.statutes
                        if statute.statutes.upper() == Etat.MESSAGE1.value.upper() or statute.statutes.upper() == Etat.MESSAGE2.value.upper() or statute.statutes.upper() == Etat.MESSAGE3.value.upper():
                            statute.statutes = Etat.SUCCESS.value
                            statute.save()

                    logger.info('__update_statute_accepted -> lancement_valide True')
                    self.lancement_valide = True

                    con = Con.objects.get(id=self.con.ID)
                    if Manager.objects.filter(idcon=con).count() <= 0:
                        m = Manager(idcon=con)
                        m.save()      
                    
                    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                    data = {
                        "description": f"Recuperation des nouvelles connexion terminée",
                        "etape": "en_cours"
                    }
                    client.publish(self.__canal, json.dumps(data))

                else:
                    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                    data = {
                        "description": f"Echec lors de l'analyse des nouvelles connexion",
                        "etape": "echec"
                    }
                    client.publish(self.__canal, json.dumps(data))

                    logger.info("LDObserver.__update_statute_accepted -> lancement valide = False test : if self.lancement_valide != False")

                    client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                    message = {
                        'action': 'STOP',
                        'object_id': str(self.con.ID)
                    }
                    client.publish('request_channel', json.dumps(message))

            else:
                client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                data = {
                    "description": f"Echec lors de l'analyse des nouvelles connexion",
                    "etape": "echec"
                }
                client.publish(self.__canal, json.dumps(data))


                self.lancement_valide = False
                logger.info('LDObserver.__update_statute_accepted -> lancement valide = False test : if not is_erreur')

                client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                message = {
                    'action': 'STOP',
                    'object_id': str(self.con.ID)
                }
                client.publish('request_channel', json.dumps(message))

        except Exception as e:

            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            data = {
                "description": f"Echec lors de l'analyse des nouvelles connexion : {e}",
                "etape": "echec"
            }
            client.publish(self.__canal, json.dumps(data))

            logger.info(f'erreur lors de la methode __update_statute_accepted : {e}')
            self.lancement_valide = False
            logger.info('lancement valide = False')

            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            message = {
                'action': 'STOP',
                'object_id': str(self.con.ID)
            }
            client.publish('request_channel', json.dumps(message))


    def normaliser_url(url):
        """Décoder et normaliser l'URL."""
        # Décodage de l'URL
        url_decoded = urllib.parse.unquote(url)
        # Suppression des barres de fin éventuelles et normalisation en minuscule
        url_cleaned = url_decoded.rstrip('/').lower()
        return url_cleaned

    @trace_function_log
    @check_connection
    def __comparer_statute(self) -> list:
        """
        Renvoie les ID des prospects ayant accepté la connexion.

        Cette méthode compare les statuts des prospects enregistrés dans la base de données avec les statuts récupérés via le navigateur LinkedIn.
        Elle procède comme suit :
        
        1. Récupère les statuts des prospects depuis la base de données via `getProspectObserver`.
        2. Tente de démarrer le navigateur LinkedIn avec le lien du compte utilisateur.
        3. Si le navigateur démarre correctement, récupère les statuts des prospects depuis LinkedIn.
        4. Compare les profils LinkedIn des prospects de la base de données avec ceux récupérés via le navigateur.
        5. Retourne une liste des ID des prospects dont le profil LinkedIn est présent dans les statuts récupérés.

        En cas d'échec du démarrage du navigateur ou d'une exception, l'état de l'utilisateur est mis à `Etat.FAILURE`, et un email est envoyé pour notifier l'utilisateur de la nécessité de mettre à jour son token de connexion.

        Returns:
            list: Liste des ID des prospects ayant accepté la connexion, ou `None` en cas d'échec.
        """
        status_bd = Prospects.objects.filter(idcon_id=self.con.ID).exclude(statutes__statutes='Accepted').values('linkedin_profile', 'id')

        # statuts_navigateur = self.__navigateur.getEtatsProspects()
        # return [e["id"] for e in status_bd if e["linkedin_profile"] in statuts_navigateur]
        try:
            client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            data = {
                "description": f"Lancement du navigateur pour la recuperation des prospects",
                "etape": "en_cours"
            }
            client.publish(self.__canal, json.dumps(data))

            con = Con.objects.get(id=self.con.ID)
         
            if self.__navigateur.start(con.linkedin_lien):
                statuts_navigateur = self.__navigateur.getEtatsProspects()
                if statuts_navigateur != False:
                    statuts_navigateur = [LDObserver.normaliser_url(l) for l in statuts_navigateur]
                    logger.info(f"different de false : {statuts_navigateur}")
                    
                    liste_accepted = [e["id"] for e in status_bd if LDObserver.normaliser_url(e["linkedin_profile"]) in statuts_navigateur]
                    
                reponse_navigateur = self.__navigateur.recuperer_reponse()
                if reponse_navigateur != False:
                    prospect_message = Prospects.objects.filter(
                        idcon_id=self.con.ID, 
                        statutes__statutes__in=['1ST', '2ND', '3RD']
                    ).values('complete_name', 'id')

                    liste_success = [e['id'] for e in prospect_message if e["complete_name"] in reponse_navigateur]
                else:
                    liste_success = []

                return [liste_accepted, liste_success]
            
            logger.info('token de connexion invalide')
            self.lancement_valide = False
            c = Con.objects.get(id=self.con.ID)
            codeerr = codeerreur.objects.get(id=2)
            if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
                e = Erreur(
                    idcon = c,
                    etat = False,
                    date_err = datetime.now(),
                    code_err = codeerr
                )
                e.save()

            return []

        except Exception as e:
            logger.info('erreur - autre : ' + e)
            self.lancement_valide = False
            c = Con.objects.get(id=self.con.ID)
            ## si n'existe pas deja
            codeerr = codeerreur.objects.get(id=2)
            if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
                e = Erreur(
                    idcon = c,
                    etat = False,
                    date_err = datetime.now(),
                    code_err = codeerr
                )
                e.save()
            return []

