# # This is an auto-generated Django model module.
# # You'll have to do the following manually to clean this up:
# #   * Rearrange models' order
# #   * Make sure each model has one field with primary_key=True
# #   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
# #   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# # Feel free to rename the models, but don't rename db_table values or field names.
# from django.db import models
# from django.contrib.auth.models import AbstractUser

# class AuthGroup(models.Model):
#     name = models.CharField(unique=True, max_length=150)

#     class Meta:
#         managed = True
#         db_table = 'auth_group'

# class AuthGroupPermissions(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
#     permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

#     class Meta:
#         managed = True
#         db_table = 'auth_group_permissions'
#         unique_together = (('group', 'permission'),)


# class AuthPermission(models.Model):
#     name = models.CharField(max_length=255)
#     content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
#     codename = models.CharField(max_length=100)

#     class Meta:
#         managed = True
#         db_table = 'auth_permission'
#         unique_together = (('content_type', 'codename'),)


# class AuthUser(models.Model):
#     password = models.CharField(max_length=128)
#     last_login = models.DateTimeField(blank=True, null=True)
#     is_superuser = models.IntegerField()
#     username = models.CharField(unique=True, max_length=150)
#     first_name = models.CharField(max_length=150)
#     last_name = models.CharField(max_length=150)
#     email = models.CharField(unique=True, max_length=254)
#     is_staff = models.IntegerField()
#     is_active = models.IntegerField()
#     date_joined = models.DateTimeField()

#     class Meta:
#         managed = True
#         db_table = 'auth_user'


# class AuthUserGroups(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     user = models.ForeignKey(AuthUser, models.DO_NOTHING)
#     group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

#     class Meta:
#         managed = True
#         db_table = 'auth_user_groups'
#         unique_together = (('user', 'group'),)


# class AuthUserUserPermissions(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     user = models.ForeignKey(AuthUser, models.DO_NOTHING)
#     permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

#     class Meta:
#         managed = True
#         db_table = 'auth_user_user_permissions'
#         unique_together = (('user', 'permission'),)


# class Campagne(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     iduser = models.ForeignKey('Users', models.DO_NOTHING, db_column='IDUser', blank=True, null=True)  # Field name made lowercase.
#     name = models.CharField(db_column='NAME', max_length=50, blank=True, null=True)  # Field name made lowercase.
#     description = models.CharField(db_column='DESCRIPTION', max_length=1000, blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'campagne'


# class Con(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     iduser = models.ForeignKey('Users', models.DO_NOTHING, db_column='IDUser', blank=True, null=True)  # Field name made lowercase.
#     token = models.CharField(max_length=1000, blank=True, null=True)
#     jouractivite = models.CharField(db_column='JourActivite', max_length=3, blank=True, null=True)  # Field name made lowercase.
#     heureactivite = models.CharField(db_column='HeureActivite', max_length=5, blank=True, null=True)  # Field name made lowercase.
#     idcampagne = models.ForeignKey(Campagne, models.DO_NOTHING, db_column='IDCampagne', blank=True, null=True)  # Field name made lowercase.
#     name = models.CharField(max_length=50, blank=True, null=True)
#     linkedin_lien = models.CharField(max_length=200, blank=True, null=True)
#     google_sheet = models.CharField(max_length=300, blank=True, null=True)
#     date_creation = models.DateField(blank=True, null=True)


#     class Meta:
#         managed = True
#         db_table = 'con'


# class DjangoAdminLog(models.Model):
#     action_time = models.DateTimeField()
#     object_id = models.TextField(blank=True, null=True)
#     object_repr = models.CharField(max_length=200)
#     action_flag = models.PositiveSmallIntegerField()
#     change_message = models.TextField()
#     content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
#     user = models.ForeignKey(AuthUser, models.DO_NOTHING)

#     class Meta:
#         managed = True
#         db_table = 'django_admin_log'


# class DjangoContentType(models.Model):
#     app_label = models.CharField(max_length=100)
#     model = models.CharField(max_length=100)

#     class Meta:
#         managed = True
#         db_table = 'django_content_type'
#         unique_together = (('app_label', 'model'),)


# class DjangoMigrations(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     app = models.CharField(max_length=255)
#     name = models.CharField(max_length=255)
#     applied = models.DateTimeField()

#     class Meta:
#         managed = True
#         db_table = 'django_migrations'


# class DjangoSession(models.Model):
#     session_key = models.CharField(primary_key=True, max_length=40)
#     session_data = models.TextField()
#     expire_date = models.DateTimeField()

#     class Meta:
#         managed = True
#         db_table = 'django_session'


# class Fonctionement(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     idcampagne = models.ForeignKey(Campagne, models.DO_NOTHING, db_column='IDCampagne', blank=True, null=True)  # Field name made lowercase.
#     type = models.CharField(db_column='TYPE', max_length=7, blank=True, null=True)  # Field name made lowercase.
#     tempsprochaineexec = models.IntegerField(db_column='TempsProchaineExec', blank=True, null=True)  # Field name made lowercase.
#     statutes_activation = models.CharField(db_column='Statutes_activation', max_length=8, blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'fonctionement'


# class Message(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     corp = models.CharField(db_column='Corp', max_length=1500, blank=True, null=True)  # Field name made lowercase.
#     idcon = models.ForeignKey(Con, models.DO_NOTHING, db_column='IDCon', blank=True, null=True)  # Field name made lowercase.
#     idfonc = models.ForeignKey(Fonctionement, models.DO_NOTHING, db_column='IDFonc', blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'message'


# class Prospects(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     idcon = models.ForeignKey(Con, models.DO_NOTHING, db_column='IDCon', blank=True, null=True)  # Field name made lowercase.
#     linkedin_profile = models.CharField(db_column='LinkedIn_Profile', max_length=100, blank=True, null=True)  # Field name made lowercase.
#     name = models.CharField(db_column='Name', max_length=50, blank=True, null=True)  # Field name made lowercase.
#     statutes = models.ForeignKey('Statutes', models.DO_NOTHING, db_column='Statutes', blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'prospects'


# class Relationteam(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     idteam = models.ForeignKey('Teams', models.DO_NOTHING, db_column='IDTeam', blank=True, null=True)  # Field name made lowercase.
#     iduser = models.ForeignKey('Users', models.DO_NOTHING, db_column='IDUser', blank=True, null=True)  # Field name made lowercase.
#     role = models.CharField(db_column='Role', max_length=13, blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'relationteam'


# class Statutes(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     statutes = models.CharField(db_column='Statutes', max_length=8, blank=True, null=True)  # Field name made lowercase.
#     changedate = models.DateField(db_column='changeDate', blank=True, null=True)  # Field name made lowercase.
#     id_prospect = models.IntegerField(db_column='ID_Prospect', blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'statutes'



# class Teams(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     creationdate = models.DateTimeField(db_column='creationDate', blank=True, null=True)  # Field name made lowercase.
#     name = models.CharField(db_column='Name', max_length=50, blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'teams'


# class Users(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'users'

# class Manager(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     idcon = models.ForeignKey(Con, models.DO_NOTHING, db_column='IDCon', blank=True, null=True)  # Field name made lowercase.

#     class Meta:
#         managed = True
#         db_table = 'manager'

# class TachesProgrammes(models.Model):
#     id = models.AutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
#     idcon = models.ForeignKey(Con, models.DO_NOTHING, db_column='IDCon', blank=True, null=True)  # Field name made lowercase.
#     heure = models.DateTimeField(db_column='heure', blank=True, null=True)

#     class Meta:
#         managed = True
#         db_table = 'tachesProgrammes'



