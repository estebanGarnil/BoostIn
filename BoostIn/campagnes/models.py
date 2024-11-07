from django.db import models



class Users(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.

    class Meta:
        db_table = 'users'

class Campagne(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    iduser = models.ForeignKey(Users, models.CASCADE, db_column='iduser')  # Field name made lowercase.
    name = models.CharField(db_column='name', max_length=50)  # Field name made lowercase.
    description = models.CharField(db_column='description', max_length=1000)  # Field name made lowercase.

    class Meta:
        db_table = 'campagne'


class Con(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    iduser = models.ForeignKey(Users, models.CASCADE, db_column='iduser')  # Field name made lowercase.
    token = models.CharField(max_length=1000)
    jouractivite = models.CharField(db_column='jouractivite', max_length=3)  # Field name made lowercase.
    heureactivite = models.CharField(db_column='heureactivite', max_length=5)  # Field name made lowercase.
    idcampagne = models.ForeignKey(Campagne, models.CASCADE, db_column='idcampagne')  # Field name made lowercase.
    name = models.CharField(max_length=50, db_column='name')
    linkedin_lien = models.CharField(max_length=200, db_column='linkedin_lien')
    google_sheet = models.CharField(max_length=300, blank=True, null=True, db_column='google_sheet')
    date_creation = models.DateField(blank=True, null=True, db_column='date_creation')

    class Meta:
        db_table = 'con'

class Fonctionement(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    idcampagne = models.ForeignKey(Campagne, models.CASCADE, db_column='idcampagne')  # Field name made lowercase.
    type = models.CharField(db_column='type', max_length=7)  # Field name made lowercase.
    tempsprochaineexec = models.IntegerField(db_column='TempsProchaineExec')  # Field name made lowercase.
    statutes_activation = models.CharField(db_column='Statutes_activation', max_length=8)  # Field name made lowercase.

    class Meta:
        db_table = 'fonctionement'


class Message(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    corp = models.CharField(db_column='corp', max_length=1500)  # Field name made lowercase.
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')  # Field name made lowercase.
    idfonc = models.ForeignKey(Fonctionement, models.CASCADE, db_column='idfonc')  # Field name made lowercase.

    class Meta:
        db_table = 'message'

class Statutes(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    statutes = models.CharField(db_column='statutes', max_length=8)  # Field name made lowercase.
    changedate = models.DateField(db_column='changeDate', auto_now_add=True)  # Field name made lowercase.
    id_prospect = models.IntegerField(db_column='id_prospect', null=True, blank=True)  # Field name made lowercase.

    class Meta:
        db_table = 'statutes'

class Prospects(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')  # Field name made lowercase.
    linkedin_profile = models.CharField(db_column='linkedin_profile', max_length=100)  # Field name made lowercase.
    name = models.CharField(db_column='name', max_length=50)  # Field name made lowercase.
    statutes = models.ForeignKey(Statutes, models.CASCADE, db_column='statutes')  # Field name made lowercase.

    class Meta:
        db_table = 'prospects'

class Manager(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')  # Field name made lowercase.

    class Meta:
        db_table = 'manager'

class TachesProgrammes(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)  # Field name made lowercase.
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')  # Field name made lowercase.
    heure = models.DateTimeField(db_column='heure')

    class Meta:
        db_table = 'tachesprogrammes'

class NomChamp(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')
    nom = models.CharField(db_column='nom', max_length=50)

    class Meta:
        db_table = 'nomchamp'

class ValeurChamp(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    id_champ = models.ForeignKey(NomChamp, models.CASCADE, db_column='idchamp')
    id_prospect = models.ForeignKey(Prospects, models.CASCADE, db_column='idprospect')
    valeur = models.CharField(db_column='valeur', max_length=300)

    class Meta:
        db_table = 'valeurchamp'


class codeerreur(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    description_code = models.CharField(db_column='description_code', max_length=300)

    class Meta:
        db_table = 'codeerreur'

class Erreur(models.Model):
    id = models.AutoField(db_column='id', primary_key=True)
    idcon = models.ForeignKey(Con, models.CASCADE, db_column='idcon')
    etat = models.BooleanField(db_column='etat')
    date_err = models.DateField(db_column='date_err')
    code_err = models.ForeignKey(codeerreur, models.CASCADE, db_column='code_err')

    class Meta:
        db_table = 'erreur_con'
