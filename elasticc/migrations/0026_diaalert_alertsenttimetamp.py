# Generated by Django 4.0.6 on 2022-08-08 16:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0025_rename_classiferid_brokerclassifier_classifierid'),
    ]

    operations = [
        migrations.AddField(
            model_name='diaalert',
            name='alertSentTimetamp',
            field=models.DateTimeField(null=True),
        ),
    ]