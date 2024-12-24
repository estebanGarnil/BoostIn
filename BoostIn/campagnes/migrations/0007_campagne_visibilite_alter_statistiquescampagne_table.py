# Generated by Django 5.0.7 on 2024-12-10 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campagnes', '0006_statistiquescampagne'),
    ]

    operations = [
        migrations.AddField(
            model_name='campagne',
            name='visibilite',
            field=models.CharField(choices=[('public', 'Public'), ('prive', 'Privé'), ('team', 'Team')], db_column='visibilite', default='public', max_length=6),
        ),
        migrations.AlterModelTable(
            name='statistiquescampagne',
            table='campagnes_statistiquescampagne',
        ),
    ]