import random
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from django.conf import settings

from datetime import datetime, timedelta, timezone

import time as tm  # Utiliser un alias pour éviter les conflits

from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from .navigateur import LinkedInNavigateur

import threading

from .Donnees import Etat, MessageObj, Prospect, EtatObj

from .email_envoyer import email_sender

from ..models import NomChamp, Prospects, TachesProgrammes, Con, Erreur, ValeurChamp, codeerreur, Message, Manager

lock = threading.Lock()

email = email_sender()

class LDManager:
    """
    Gère toutes les instances de `LDCon`.

    La classe `LDManager` est responsable de la création, du suivi, de la gestion, et de l'exécution d'instances de `LDCon`. 
    Elle permet d'ajouter, de supprimer, de démarrer, d'arrêter, et de programmer des objets `LDCon` via diverses méthodes. 
    `LDManager` utilise un gestionnaire de tâches en arrière-plan (`BackgroundScheduler`) pour planifier les exécutions à des moments précis.

    Attributs:
        objets (dict): Un dictionnaire stockant les instances de `LDCon` gérées par cette classe, avec les identifiants comme clés.
        __taches (BackgroundScheduler): Un gestionnaire de tâches en arrière-plan utilisé pour programmer les exécutions à des moments précis.
    
    Méthodes:
        __init__(): Initialise l'objet LDManager en créant un dictionnaire d'objets `LDCon` et en lançant la première tâche.
        started(id): Vérifie si un objet `LDCon` est en cours d'exécution.
        get(id): Récupère un objet `LDCon` en fonction de son identifiant.
        supr(id): Supprime un objet `LDCon` du gestionnaire.
        add(id): Ajoute un nouvel objet `LDCon` au gestionnaire.
        start(id): Démarre un objet `LDCon`.
        stop(id): Arrête un objet `LDCon`.
        programmer_activation(): Programme l'activation de chaque objet `LDCon`.
        etat(id): Renvoie l'état ou les erreurs en cours pour un objet `LDCon`.
        message_erreur(id): Renvoie le message d'erreur associé à un objet `LDCon`.
        prochaine_exec(id): Renvoie la date et l'heure de la prochaine exécution d'un objet `LDCon`.
        lancement(): Programme l'exécution de la méthode `programmer_activation` à une heure spécifique.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LDManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.objets = {}
            cls._instance.taches = BackgroundScheduler()     

            DATABASE_URL = f"mysql+pymysql://{settings.DATABASES['default']['USER']}:{settings.DATABASES['default']['PASSWORD']}@" \
                   f"{settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}/{settings.DATABASES['default']['NAME']}"

            cls._instance.taches.add_jobstore('sqlalchemy', url=DATABASE_URL)

            cls._instance.taches.start()
            manage = Manager.objects.all()
            for m in manage:
                cls._instance.objets[str(m.idcon.id)] = LDCon(m.idcon.id)

        return cls._instance 

    def attribution_horaire(self, h1 : int, h2 : int, j1:str, j2:str, _id : str, nb_exec : int=None):
        JOUR = {'1' : 'mon', '2' : 'tue', '3' : 'wed', '4' : 'thu', '5' : 'fri', '6' : 'sat', '7' : 'sun'}
        day = JOUR[j1]+'-'+JOUR[j2]
        if _id[0] == 'C':            
            f = (h2*60 - h1*60) / (nb_exec + 1)
    
            trigger = CronTrigger(
                day_of_week=day,  # Exécuter du lundi au vendredi
                hour=f"{h1}-{int(h2) - 1}",  # Exclure la dernière heure (fin exclue)
                minute=f'*/{int(f)}'  # Exécuter tous les "f" minutes
            )
            self.taches.add_job(LDManager._execute_task, trigger, id=_id, replace_existing=True, args=[str(_id)])

        elif _id[1:4] == 'CON':
            trigger = CronTrigger(
                hour=h1, 
                minute=0, 
                day_of_week=day
                )
            self.taches.add_job(LDManager._execute_task, trigger=trigger, replace_existing=True, id=_id, args=[str(_id)])

    @staticmethod
    def _execute_task(_id):
        print('execution tache id: '+_id)
        m = LDManager()
        if _id[0] == 'C':
            print('C')
            _id = _id[-2:]
            print('lancement')
            ldc = m.objets[_id].get_connexion()
            print('get_connexion')
            ldc.demander_connexion()
            print('start')
        elif _id[0:2] == '1CON':
            _id = _id[-2:]
            m.objets[_id].start()
        elif _id[0:2] == '2CON':
            _id = _id[-2:]
            m.objets[_id].stop()

    def prochaine_execution(self, _id : str) -> datetime:
        job = self.taches.get_job(_id)
        if job:
            return job.next_run_time
        # elif str(_id[-2:]) in self.objets.keys():
        #     self.start(str(_id[-2:]))
        #     return job.next_run_time
        else:
            return None
    
    def add(self, _id) -> None:
        self.objets[_id] = LDCon(ID=_id)

    def start(self, id, exe=True) -> None:
        self.objets[id].start_programmer_tache()
        self.objets[id].start(exe)

    def start_demarage(self) -> None:
        for _id in self.objets.keys():
            self.start(_id)
    
    def stop(self, _id) -> None:
        job = self.taches.get_job('C'+str(_id))
        if job:
            self.taches.remove_job('C'+str(_id))
        job = self.taches.get_job('1CON'+str(_id))
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
            print(e)

        self.objets[str(_id)].stop()
        del self.objets[str(_id)]

    def etat_lancement(self, id) -> None:
        return self.objets[id].lancement_reussi()

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
    
    def __recuperer_token(self) -> str:
        c = Con.objects.get(id=self.ID)
        return str(c.token)[2:-1]

    def get_connexion(self):
        print('get_connexion')
        return self.__connexion
    
    def start_programmer_tache(self):
        c = Con.objects.get(id=self.ID)
        m = LDManager()
        m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='1CON'+str(c.id))
        m.attribution_horaire(h1=int(c.heureactivite[3:5]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], _id='2CON'+str(c.id))

    def start(self, exe=True):
        if exe:
            a = self.__observer.start()
            b = self.__message.start()
        c = self.__connexion.start()
    
    def lancement_reussi(self) -> bool:
        return self.__observer.lancement_valide
    
    def stop(self):
        del self.__connexion
        del self.__observer
        del self.__message

class LDC:
    """
    Gestionnaire des connexions.

    La classe `LDC` est responsable de la gestion des connexions avec des prospects via LinkedIn. 
    Elle gère les tâches liées à la connexion, telles que la récupération des prospects, la programmation des envois de demandes de connexion, 
    et la gestion des fréquences d'exécution. Elle utilise un gestionnaire de tâches en arrière-plan pour planifier les exécutions à des moments précis.

    Attributs:
        __user (LDCon): Instance de l'objet `LDCon` représentant l'utilisateur.
        __navigateur (LinkedInNavigateur): Instance du navigateur LinkedIn utilisé pour envoyer des demandes de connexion.
        __taches (BackgroundScheduler): Gestionnaire de tâches en arrière-plan utilisé pour programmer les exécutions.
        __prospect (list): Liste des prospects récupérés pour l'utilisateur.
        __CpJ (float): Nombre de connexions par jour calculé.
        __frequence (timedelta): Fréquence à laquelle les actions doivent se répéter.

    Méthodes:
        __init__(user: LDCon, bdd: LDDB, navigateur: LinkedInNavigateur) -> None: Initialise l'objet LDC.
        __exit__() -> None: Arrête le gestionnaire de tâches lors de la destruction de l'objet.
        start() -> None: Lance l'objet LDC en récupérant les prospects et en programmant les envois.
        prochaine_exec() -> datetime or None: Renvoie la date et l'heure de la prochaine exécution planifiée.
        stop() -> None: Arrête tous les processus en cours.
        __calculer_frequence() -> timedelta: Calcule la fréquence à laquelle l'action doit se répéter.
        __update_prospect_on_hold() -> None: Change le statut du prospect dans la base de données.
        __recuperer_prospect() -> None: Récupère la liste des prospects pour les heures d'activités sélectionnées.
        __programmer_envoi() -> None: Programme l'envoi des tâches pour chaque prospect.
        __run_in_thread(func) -> callable: Exécute une fonction dans un nouveau thread.
        tempsProchaineExecution() -> None: Méthode de développement pour voir les prochaines exécutions programmées.
        __demander_connexion() -> None: Envoie une demande de connexion à un prospect.
    """
    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur) -> None:
        self.con : LDCon = user  # l'id de con dans la base de donnée
        self.__navigateur : LinkedInNavigateur = navigateur ## le navigateur pour pouvoir lancer des instance de chrome
        self.__CpJ : int = 20 ## connexion par jour
        self.lancement_valide = None

        self.etat = EtatObj.STOP

    def start(self) -> None:
        self.__programmer_envoi()
        self.etat = EtatObj.RUNNING
    
    def __programmer_envoi(self) -> None:
        """
        Programme l'envoi des tâches pour chaque prospect.
        """
        c = Con.objects.get(id=self.con.ID)
        m = LDManager()
        m.attribution_horaire(h1=int(c.heureactivite[0:2]), h2=int(c.heureactivite[3:5]), j1=c.jouractivite[0], j2=c.jouractivite[2], nb_exec=self.__CpJ, _id='C'+str(c.id))

    def demander_connexion(self) -> None:

        p = Prospects.objects.filter(idcon__id=self.con.ID, statutes__statutes='not sent').first()
        if self.__navigateur.start(p.linkedin_profile):
            print('essai')
            ## cas de base -> le prospect à été ajouté
            etat : Etat = self.__navigateur.connexion()
            print(p.statutes.statutes)
            s = p.statutes
            s.statutes = etat.value
            s.save()
            p.save()
            print(p.statutes.statutes)
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
    """
    Gestionnaire des messages.

    La classe `LDM` est responsable de la gestion et de l'envoi des messages aux prospects via LinkedIn. Elle interagit avec la base de données pour récupérer les messages et les prospects, 
    et utilise un navigateur LinkedIn pour envoyer les messages. La classe gère également la planification des tâches d'envoi via un gestionnaire de tâches en arrière-plan.

    Attributs:
        __user (LDCon): Instance de l'objet `LDCon` représentant l'utilisateur.
        __navigateur (LinkedInNavigateur): Instance du navigateur LinkedIn utilisé pour envoyer des messages.
        __taches (BackgroundScheduler): Gestionnaire de tâches en arrière-plan utilisé pour programmer les envois.
        __prospect (list): Liste des prospects récupérés pour l'utilisateur.
        __message (list): Liste des messages à envoyer.

    Méthodes:
        __init__(user: LDCon, bdd: LDDB, navigateur: LinkedInNavigateur): Initialise l'objet LDM avec les attributs nécessaires.
        start() -> None: Démarre le processus d'envoi de messages.
        __recuperer_message() -> None: Récupère les messages associés à l'utilisateur depuis la base de données et initialise les objets `Message`.
        __recuperer_prospect() -> None: Ajoute les prospects à traiter pour chaque message.
        __envoyer_message() -> None: Envoie les messages prévus à tous les prospects dans la liste pour chaque instance de message.
        __run_in_thread(func) -> callable: Exécute une fonction dans un nouveau thread.
    """

    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur):
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur

        self.__taches : BackgroundScheduler = BackgroundScheduler()
        self.__prospect : Prospect = []
        self.__message : MessageObj = []
    
    def start(self) -> None:
        self.__recuperer_message()
        self.__recuperer_prospect()

        self.__envoyer_message()
    
    def __recuperer_message(self) -> None:
        """
        Récupère les messages associés à l'utilisateur depuis la base de données et initialise les objets `Message`.
        """
        message = Message.objects.filter(idcon__iduser_id=self.con.ID).values('id', 'corp', 'idfonc__tempsprochaineexec', 'idfonc__statutes_activation', 'idfonc__type')
        i = 0
        for m in message:
            self.__message.append(MessageObj(m[0], m[1], m[2], Etat(m[3])))
            i+=1
    
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
        if self.con.etat != Etat.FAILURE:
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
    """
    Observe si de nouveaux prospects ont accepté une demande de connexion et met à jour les prospects ayant accepté.

    La classe `LDObserver` est responsable de surveiller les réponses aux demandes de connexion envoyées sur LinkedIn et de mettre à jour la base de données 
    pour refléter les prospects qui ont accepté la connexion. Elle utilise un gestionnaire de tâches pour planifier les vérifications et les mises à jour.

    Attributs:
        __user (LDCon): Instance de l'objet `LDCon` représentant l'utilisateur.
        __navigateur (LinkedInNavigateur): Instance du navigateur LinkedIn utilisé pour surveiller les statuts des prospects.
        __taches (BackgroundScheduler): Gestionnaire de tâches en arrière-plan utilisé pour programmer les vérifications.

    Méthodes:
        __init__(user: LDCon, bdd: LDDB, navigateur: LinkedInNavigateur) -> None: Initialise l'objet LDObserver avec les attributs nécessaires.
        start() -> None: Démarre le processus d'observation des prospects.
        stop() -> None: Arrête tous les processus d'observation en cours.
        __programmer_envoi() -> None: Programme les heures d'activation pour vérifier les statuts des prospects.
        __run_in_thread(func) -> callable: Exécute une fonction dans un nouveau thread.
        __update_statute_accepted() -> None: Met à jour le statut de chaque prospect qui a accepté la connexion.
        __comparer_statute() -> list: Renvoie les ID des prospects ayant accepté la connexion.
    """

    def __init__(self, user : LDCon, navigateur : LinkedInNavigateur) -> None:
        self.con : LDCon = user 
        self.__navigateur : LinkedInNavigateur = navigateur
        self.lancement_valide = None
    
    def start(self) -> None:
        self.__update_statute_accepted()
    
    def __update_statute_accepted(self) -> None:
        """
        Met à jour le statut de chaque prospect.

        Cette méthode met à jour le statut des prospects pour indiquer qu'ils ont accepté la connexion. Après une attente de 5 secondes, 
        elle vérifie que l'utilisateur n'est pas en état d'échec (`Etat.FAILURE`). Si ce n'est pas le cas, elle verrouille les ressources partagées, 
        appelle la méthode `__comparer_statute()` pour obtenir la liste des prospects concernés, puis met à jour le statut de chaque prospect 

        Returns:
            None
        """
        tm.sleep(5)
        if self.con.etat != Etat.FAILURE:    
            l = self.__comparer_statute()
            for e in l:
                prospect = Prospects.objects.get(id=e)
                statute = prospect.statutes
                statute.statutes = Etat.ACCEPTED.value
                statute.save()

            print('lancement_valie True')
            self.lancement_valide = True
        print('lancement_valie None')


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
                print('etat des prospects')
                return [e["id"] for e in status_bd if e["linkedin_profile"] in statuts_navigateur]
            else:
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

        except:
            print('erreur - autre')
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

