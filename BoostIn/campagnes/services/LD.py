import random
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from django.conf import settings

from datetime import datetime, timedelta, timezone

import time as tm  # Utiliser un alias pour éviter les conflits

from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import zoneinfo

from .navigateur import LinkedInNavigateur

import threading

from .Donnees import Etat, MessageObj, Prospect, EtatObj

from .email_envoyer import email_sender

from ..models import NomChamp, Prospects, TachesProgrammes, Con, Erreur, ValeurChamp, codeerreur, Message, Manager

from .trace import trace_function_log

lock = threading.Lock()

email = email_sender()

import logging

logger = logging.getLogger(__name__)

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

        if _id[0] == 'C':            
            start_time = datetime.now().replace(hour=h1, minute=0, second=0, microsecond=0)
            end_time = datetime.now().replace(hour=h2, minute=0, second=0, microsecond=0)
            
            time_slots = self.generate_non_overlapping_times(start_time, end_time, nb_exec)
            
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
            trigger = CronTrigger(
                hour=h1, 
                minute=0, 
                day_of_week=day
                )
            self.taches.add_job(LDManager._execute_task, trigger=trigger, replace_existing=True, id=_id, args=[str(_id)])

        # JOUR = {'1' : 'mon', '2' : 'tue', '3' : 'wed', '4' : 'thu', '5' : 'fri', '6' : 'sat', '7' : 'sun'}
        # day = JOUR[j1]+'-'+JOUR[j2]
        # if _id[0] == 'C':            
        #     f = (h2*60 - h1*60) / (nb_exec + 1)
    
        #     trigger = CronTrigger(
        #         day_of_week=day,  # Exécuter du lundi au vendredi
        #         hour=f"{h1}-{int(h2) - 1}",  # Exclure la dernière heure (fin exclue)
        #         minute=f'*/{int(f)}'  # Exécuter tous les "f" minutes
        #     )
        #     self.taches.add_job(LDManager._execute_task, trigger, id=_id, replace_existing=True, args=[str(_id)])

        # elif _id[1:4] == 'CON':
        #     trigger = CronTrigger(
        #         hour=h1, 
        #         minute=0, 
        #         day_of_week=day
        #         )
        #     self.taches.add_job(LDManager._execute_task, trigger=trigger, replace_existing=True, id=_id, args=[str(_id)])
    @trace_function_log
    def generate_non_overlapping_times(self, start_time, end_time, nb_exec):
        time_slots = []
        attempts = 0
        max_attempts = nb_exec * 50  # Éviter les boucles infinies
        while len(time_slots) < nb_exec and attempts < max_attempts:
            random_minutes = random.randint(0, int((end_time - start_time).total_seconds() // 60))
            exec_time = start_time + timedelta(minutes=random_minutes)
            if exec_time not in self.existing_times:
                logger.info(f"heure aleatoire generée : {exec_time}")
                time_slots.append(exec_time)
                self.existing_times.add(exec_time)
            attempts += 1
        logger.info(f"Nombre d'horaire dans la journée: {len(time_slots)}")
        if len(time_slots) < nb_exec:
            logger.warning("Impossible de planifier toutes les tâches sans chevauchement.")
        return time_slots

    @trace_function_log
    @staticmethod
    def _execute_task(_id):
        m = LDManager()
        if _id[0] == 'C':
            _id = _id[-2:]
            ldc = m.objets[_id].get_connexion()
            ldc.demander_connexion()
        elif _id[0:2] == '1CON':
            _id = _id[-2:]
            m.objets[_id].start()
        elif _id[0:2] == '2CON':
            _id = _id[-2:]
            m.objets[_id].stop()
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

            

        job = self.taches.get_job(_id)
        if job:
            return job.next_run_time
        # elif str(_id[-2:]) in self.objets.keys():
        #     self.start(str(_id[-2:]))
        #     return job.next_run_time
        else:
            return None
    @trace_function_log
    def add(self, _id) -> None:
        self.objets[_id] = LDCon(ID=_id)
    @trace_function_log
    def start(self, id, exe=True) -> None:
        self.objets[id].start_programmer_tache()
        self.objets[id].start(exe)
    @trace_function_log
    def start_demarage(self) -> None:
        for _id in self.objets.keys():
            self.start(_id)
    @trace_function_log
    def stop(self, _id) -> None:
        job = self.taches.get_job('C'+str(_id))
        logger.info(f'job supression : {job}')
        if job:
            self.taches.remove_job('C'+str(_id))
        job = self.taches.get_job('1CON'+str(_id))
        logger.info(f'job supression 1CON : {job}')
        if job:
            self.taches.remove_job('1CON'+str(_id))
        logger.info(f'job supression 2CON : {job}')
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
    def add_manager(self, _id) -> None:
        con = Con.objects.get(id=_id)
        if Manager.objects.filter(idcon=con).count() <= 0:
            m = Manager(idcon=con)
            m.save()      

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
    def __init__(self, ID : int) -> None:
        self.ID : int = ID
        self.__token_ld : str = self.__recuperer_token()
        self.__navigateur : LinkedInNavigateur = LinkedInNavigateur(self.__token_ld)

        self.__connexion : LDC = LDC(self, self.__navigateur)
        self.__observer : LDObserver = LDObserver(self, self.__navigateur)
        self.__message : LDM = LDM(self, self.__navigateur)

        self.etat = None
    @trace_function_log
    def __recuperer_token(self) -> str:
        c = Con.objects.get(id=self.ID)
        logger.info("token : {c.token}")
        return str(c.token)
    @trace_function_log
    def get_connexion(self):
        return self.__connexion
    @trace_function_log
    def start_programmer_tache(self):
        c = Con.objects.get(id=self.ID)
        m = LDManager()
        m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='1CON'+str(c.id))
        m.attribution_horaire(h1=int(c.heureactivite[3:5]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='2CON'+str(c.id))
    @trace_function_log
    def start(self, exe=True):
        if exe:
            a = self.__observer.start()
            b = self.__message.start()
        c = self.__connexion.start()
    @trace_function_log
    def lancement_reussi(self) -> bool:
        return self.__observer.lancement_valide
    @trace_function_log
    def stop(self):
        del self.__connexion
        del self.__observer
        del self.__message

class LDC:
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur) -> None:
        self.con : LDCon = user  # l'id de con dans la base de donnée
        self.__navigateur : LinkedInNavigateur = navigateur ## le navigateur pour pouvoir lancer des instance de chrome
        self.__CpJ : int = 20 ## connexion par jour
        self.lancement_valide = None

        self.etat = EtatObj.STOP
    @trace_function_log
    def start(self) -> None:
        self.__programmer_envoi()
        self.etat = EtatObj.RUNNING
    @trace_function_log
    def __programmer_envoi(self) -> None:
        """
        Programme l'envoi des tâches pour chaque prospect.
        """
        c = Con.objects.get(id=self.con.ID)
        m = LDManager()
        m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], nb_exec=self.__CpJ, _id='C'+str(c.id))
    @trace_function_log
    def demander_connexion(self) -> None:

        p = Prospects.objects.filter(idcon__id=self.con.ID, statutes__statutes='not sent').first()
        if self.__navigateur.start(p.linkedin_profile):
            ## cas de base -> le prospect à été ajouté
            etat : Etat = self.__navigateur.connexion()
            s = p.statutes
            s.statutes = etat.value
            s.save()
            p.save()
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

class LDM:
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur):
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur

        self.__taches : BackgroundScheduler = BackgroundScheduler()
        self.__prospect : Prospect = []
        self.__message : MessageObj = []
    @trace_function_log
    def start(self) -> None:
        self.__recuperer_message()
        self.__recuperer_prospect()

        self.__envoyer_message()
    @trace_function_log
    def __recuperer_message(self) -> None:
        """
        Récupère les messages associés à l'utilisateur depuis la base de données et initialise les objets `Message`.
        """
        message = Message.objects.filter(idcon__iduser_id=self.con.ID).values('id', 'corp', 'idfonc__tempsprochaineexec', 'idfonc__statutes_activation', 'idfonc__type')
        i = 0
        for m in message:
            self.__message.append(MessageObj(m[0], m[1], m[2], Etat(m[3])))
            i+=1
    @trace_function_log
    def __recuperer_prospect(self) -> None:
        """
        Ajoute les prospects à traiter pour chaque message.
        """
        for m in self.__message:
            prospect = Prospects.objects.filter(
                idcon__iduser_id=self.con.ID,
                statutes__statutes=m.statut.value,
                statutes__changedate__lte=timezone.now() - timedelta(days=m.jour)
                ).values('id', 'name', 'linkedin_profile')
            for p in prospect:
                corp = m.corp

                var = re.findall(r'#(.*?)#', corp)

                for v in var:
                    variable = NomChamp.objects.get(idcon=self.con.ID, nom=v)
                    p = Prospects.objects.get(id=p[0])

                    val = ValeurChamp.objects.get(id_prospect=p, id_champ=variable)

                    corp.replace(f'#{v}#', val.valeur)
        
                m.prospect.append(Prospect(p[0], p[1], p[2], corp))
    @trace_function_log
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
        c = Con.objects.get(id=self.con.ID)
        codeerr = codeerreur.objects.get(id=2)
        if Erreur.objects.filter(idcon=c, etat=0, code_err=codeerr).count() == 0:
            if self.__navigateur.start(c.linkedin_lien):
                for m in self.__message:
                    for p in m.prospect:
                        self.__navigateur.getPage(p.lien)
                        envoi = self.__navigateur.envoiMessage(p.corp)

                        if envoi == Etat.SENT:
                            prospect = Prospects.objects.get(id=p.ID)
                            statute = prospect.statutes
                            statute.statutes = m.statut.suivant().value
                            statute.save()

                        if envoi == Etat.SUCCESS:
                            prospect = Prospects.objects.get(id=p.ID)
                            statute = prospect.statutes
                            statute.statutes = Etat.SUCCESS.value
                            statute.save()

                        tm.sleep(random.randint(1,3))
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
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur) -> None:
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur
        self.lancement_valide = None
    @trace_function_log
    def start(self) -> None:
        self.__update_statute_accepted()
    @trace_function_log
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
                if self.lancement_valide != False:
                    logger.info(f"__update_statute_accepted -> {l}")
                    for e in l:
                        logger.info(f'__update_statute_accepted -> {e}')
                        prospect = Prospects.objects.get(id=e)
                        statute = prospect.statutes
                        logger.info(f'LDObserver.__update_statute_accepted -> {statute.statutes}')
                        logger.info(f'Etat.SENT.value : {Etat.SENT.value} | Etat.ON_HOLD : {Etat.ON_HOLD}')
                        if statute.statutes.upper() == Etat.ON_HOLD.value.upper() or statute.statutes.upper() == Etat.NOT_SENT.value.upper():
                            logger.info(f"Maj du prospect {statute.statutes} -> {Etat.ACCEPTED.value} ")
                            statute.statutes = Etat.ACCEPTED.value
                            statute.save()
                    logger.info('__update_statute_accepted -> lancement_valide True')
                    self.lancement_valide = True
                else:
                    logger.info("LDObserver.__update_statute_accepted -> lancement valide = False test : if self.lancement_valide != False")
            else:
                self.lancement_valide = False
                logger.info('LDObserver.__update_statute_accepted -> lancement valide = False test : if not is_erreur')
        except Exception as e:
            logger.info(f'erreur lors de la methode __update_statute_accepted : {e}')
            self.lancement_valide = False
            logger.info('lancement valide = False')

    @trace_function_log
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
            con = Con.objects.get(id=self.con.ID)
         
            if self.__navigateur.start(con.linkedin_lien):
                statuts_navigateur = self.__navigateur.getEtatsProspects()
                if statuts_navigateur != False:
                    logger.info(f"different de false : {statuts_navigateur}")
                    return [e["id"] for e in status_bd if e["linkedin_profile"] in statuts_navigateur]
            
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

