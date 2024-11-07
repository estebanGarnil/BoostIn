from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

class Manager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Manager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init_manager(self):
        self.taches = BackgroundScheduler = BackgroundScheduler()        
        self.objets = {}

    def attribution_horaire(self, h1, h2, nb_exec):
        f = (h2-h1) / (nb_exec+1) # sur que rentre dans journée d'exec
        frequence = timedelta(minutes=f)

        self.taches.add_job(self.start, 'interval', minutes=frequence)
    

# Usage
singleton1 = Manager()
singleton2 = Manager()

print(singleton1 is singleton2)  # Affiche: True

