# Generated by Django 4.1.2 on 2022-10-24 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0035_diaobjecttruth_galnmatch_alter_diaobjecttruth_galid_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brokerclassification',
            name='classId',
            field=models.IntegerField(db_index=True),
        ),
    ]