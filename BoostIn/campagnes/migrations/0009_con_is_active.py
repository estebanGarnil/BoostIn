# Generated by Django 5.0.7 on 2024-12-19 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campagnes', '0008_prospects_complete_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='con',
            name='is_active',
            field=models.BooleanField(db_column='is_active', default=False),
        ),
    ]