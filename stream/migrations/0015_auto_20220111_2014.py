# Generated by Django 3.2.11 on 2022-01-11 20:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stream', '0014_rename_ra_decl_cov_elasticcdiasource_ra_decl_cov'),
    ]

    operations = [
        migrations.AlterField(
            model_name='elasticcalert',
            name='alertId',
            field=models.BigIntegerField(db_index=True),
        ),
        migrations.AddField(
            model_name='elasticcalert',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
            preserve_default=False,
        ),
    ]