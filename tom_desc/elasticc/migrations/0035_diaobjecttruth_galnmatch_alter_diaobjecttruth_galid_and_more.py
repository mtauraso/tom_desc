# Generated by Django 4.1.1 on 2022-10-03 20:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0034_brokerclassifier_elasticc_br_brokern_42e68f_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='diaobjecttruth',
            name='galnmatch',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='diaobjecttruth',
            name='galid',
            field=models.BigIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='diaobjecttruth',
            name='galsnddlr',
            field=models.FloatField(null=True),
        ),
        migrations.AlterField(
            model_name='diaobjecttruth',
            name='galsnsep',
            field=models.FloatField(null=True),
        ),
        migrations.AlterField(
            model_name='diaobjecttruth',
            name='galzphot',
            field=models.FloatField(null=True),
        ),
        migrations.AlterField(
            model_name='diaobjecttruth',
            name='galzphoterr',
            field=models.FloatField(null=True),
        ),
    ]