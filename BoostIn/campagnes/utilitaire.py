from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.db import transaction

from .services.Donnees import Etat
from .utils import automatisation
from .models import Con, Fonctionement, NomChamp, Prospects, Statutes, Users, Campagne, ValeurChamp, Message, Erreur, codeerreur

def fetch_google_sheet_data(sheet_id):
    # Configuration des permissions de l'API
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    # Charger les credentials
    creds = ServiceAccountCredentials.from_json_keyfile_name('campagnes/boostin-430720-5e3a7e10c049.json', scope)

    # Autoriser et accéder à la feuille
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1

    # Récupérer toutes les données
    return sheet.get_all_records()

def clean_lien(lien):
    s = str(lien)
    s = s[s.index("/d/")+3:]
    return s[:s.index("/")]

class InsertionForm:
    def __init__(self, form, id_campagne, id_message, edit) -> None:
        self.form =  form
        self.con_instance = None 
        self.message_instance = None 
        self.edit = edit
        
        if id_campagne:
            self.con_instance = Con.objects.get(id=id_campagne)
        if id_message:
            self.message_instance = Message.objects.get(id=int(id_message))
        
        # self.edit = type(id_campagne) != type(id_message) ## si deux None alors pas modification

    def insert_con(self, request):
        chaine_jour = str(self.form.cleaned_data['jour_debut'])+"-"+str(self.form.cleaned_data['jour_fin'])
        chaine_heure = "{:02}".format(int(self.form.cleaned_data['heure_debut']))+"-"+"{:02}".format(int(self.form.cleaned_data['heure_fin']))
        changement_heure = False
        if self.edit:
            if self.con_instance.jouractivite != chaine_jour or self.con_instance.heureactivite != chaine_heure: ## change les heures
                self.con_instance.jouractivite = chaine_jour
                self.con_instance.heureactivite = chaine_heure
                if automatisation.prochaine_execution('C'+str(self.con_instance.id)) != None: ## est deja lancé ou non 
                    changement_heure = True

            if str(self.con_instance.token)[2:-1] != self.form.cleaned_data['token'] and Erreur.objects.filter(idcon=self.con_instance.id, code_err=codeerreur.objects.get(id=2), etat=0).count() > 0:
                e = Erreur.objects.get(idcon=self.con_instance.id, code_err=codeerreur.objects.get(id=2), etat=0)
                e.etat = 1
                e.save()

            self.con_instance.token = self.form.cleaned_data['token']
            self.con_instance.name = self.form.cleaned_data['nom_campagne']
            self.con_instance.linkedin_lien = self.form.cleaned_data['compte_linkedin']
        else:
            self.con_instance = Con(
            iduser=Users(request.user.id),
            token=self.form.cleaned_data['token'],
            jouractivite=chaine_jour,
            heureactivite=chaine_heure,
            idcampagne=Campagne.objects.get(id=self.form.cleaned_data['type']),
            name=self.form.cleaned_data['nom_campagne'],
            linkedin_lien = self.form.cleaned_data['compte_linkedin'],
            date_creation = date.today()
            )
        self.con_instance.save()

        if changement_heure:
            automatisation.stop(str(self.con_instance.id))
            automatisation.add(str(self.con_instance.id))
            automatisation.add_manager(str(self.con_instance.id))
            automatisation.start(str(self.con_instance.id), False)

    
        return self.con_instance.id

    def insert_message(self, request, step):
        if self.edit and self.message_instance is not None:
            self.message_instance.corp = self.form.cleaned_data['corp']
        else:
            
            self.message_instance = Message(
                corp=self.form.cleaned_data['corp'],
                idcon=self.con_instance,
                idfonc=Fonctionement.objects.get(idcampagne=self.con_instance.idcampagne, statutes_activation=Etat.from_number(step).value)
            )
        self.message_instance.save()

        return step >= Fonctionement.objects.filter(idcampagne=self.con_instance.idcampagne).count()

    def insert_prospect(self):
        if self.form.cleaned_data['sheet']:
            col_principale = self.form.cleaned_data['col_principale']
            col_nom = self.form.cleaned_data['col_nom']
            id_sheet = clean_lien(self.form.cleaned_data['sheet'])
            prospect_data = fetch_google_sheet_data(id_sheet)

            # Crée une transaction pour garantir la cohérence des données
            with transaction.atomic():
                # Création des champs avec bulk_create pour éviter de multiples save()
                id_champ = [
                    NomChamp(idcon=self.con_instance, nom=k)
                    for k in prospect_data[0].keys()
                ]
                NomChamp.objects.bulk_create(id_champ)
                
                # Récupération des linkedin_profile existants
                existing_profiles = set(
                    Prospects.objects.filter(idcon=self.con_instance)
                    .values_list('linkedin_profile', flat=True)
                )

                statutes_to_create = []
                for l in prospect_data:
                    if l[col_principale] not in existing_profiles:
                        # Crée un Statutes pour chaque prospect
                        statutes_to_create.append(Statutes(statutes='Not sent'))

                # Enregistre tous les Statutes d'abord
                Statutes.objects.bulk_create(statutes_to_create)

                # Crée les Prospects en associant les objets Statutes sauvegardés
                prospects_to_create = []
                valeurs_to_create = []
                for l, statut_prospect in zip(prospect_data, statutes_to_create):
                    if l[col_principale] not in existing_profiles:
                        prospect_instance = Prospects(
                            idcon=self.con_instance,
                            linkedin_profile=l[col_principale],
                            name=l[col_nom],
                            statutes=statut_prospect
                        )
                        prospects_to_create.append(prospect_instance)

                        # Crée un ValeurChamp pour chaque champ lié au prospect
                        valeurs_to_create.extend([
                            ValeurChamp(
                                id_prospect=prospect_instance,
                                id_champ=v,
                                valeur=l[v.nom]
                            ) for v in id_champ
                        ])

                # Bulk create pour Prospects et ValeurChamp
                Prospects.objects.bulk_create(prospects_to_create)
                ValeurChamp.objects.bulk_create(valeurs_to_create)





