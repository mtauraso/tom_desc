# Generated by Django 4.1.7 on 2023-02-24 21:05

from django.db import migrations, models
import django.db.models.deletion
import psqlextra.backend.migrations.operations.add_default_partition
import psqlextra.backend.migrations.operations.create_partitioned_model
import psqlextra.manager.manager
import psqlextra.models.partitioned
import psqlextra.types


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0037_prevsourcecounts_view'),
    ]

    # This was manually created by RKNOP on 2023-02-24, with the
    # goal of converting the existing elasticc_brokerclassifications table
    # to a partitioned table.
    #
    # * Started by making a trash migration with just the state
    #   operations to create a new table (with a temporary name) that
    #   is just like the partitioned elasticc_brokerclassification table
    #
    # * Added dropping of BrokerClassification to state operations
    #
    # * Moved the code from the trash migration to state_operations,
    #   renaming the table it is operating on as BrokerClassification.
    #
    # * Copied the SQL from python manage.py sqlmigrate ... on the trash
    #   migration into database_operations, renaming the table to
    #   elasticc_brokerclassification, and adding the code necessary to
    #   rename the existing elasticc_brokerclassification table to
    #   elasticc_brokerclassification_default and add it as the default
    #   partition.  (Note that I don't rename all the indexes.  They
    #   have random barf at the end, which, alas, does not show up
    #   explicition in previous migrations, but is left to django to
    #   generate.  As such, I can't be sure what those indexes will be
    #   named, so I'll just leave them with not really the right name in
    #   the elasticc_brokerclassification_default table, and figure that
    #   the random barf will avoid name collisions.)
    
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE elasticc_brokerclassification RENAME TO elasticc_brokerclassification_default',
                    reverse_sql=( 'ALTER TABLE elasticc_brokerclassification_default '
                                  'RENAME TO elasticc_brokerclassification' )
                ),
                migrations.RunSQL(
                    sql=( 'ALTER TABLE elasticc_brokerclassification_default '
                          'DROP CONSTRAINT elasticc_brokerclassification_pkey' ),
                    reverse_sql=( 'ALTER TABLE elasticc_brokerclassification_default '
                                  'ADD CONSTRAINT elasticc_brokerclassification_pkey '
                                  'PRIMARY KEY ("classificationId")' )
                ),
                migrations.RunSQL(
                    sql=( 'ALTER TABLE elasticc_brokerclassification_default '
                          'ADD CONSTRAINT elasticc_brokerclassification_default_pkey '
                          'PRIMARY KEY ("classificationId", "classifierId")' ),
                    reverse_sql=( 'ALTER TABLE elasticc_brokerclassification_default '
                                  'DROP CONSTRAINT elasticc_brokerclassification_default_pkey' )
                ),
                migrations.RunSQL(
                    sql=( 'CREATE TABLE "elasticc_brokerclassification" '
                          '("classificationId" bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY, '
                          ' "classifierId" bigint NOT NULL, '
                          ' "classId" integer NOT NULL, '
                          ' "probability" double precision NOT NULL, '
                          ' "modified" timestamp with time zone NOT NULL, '
                          ' "brokerMessageId" bigint NULL, '
                          ' PRIMARY KEY ("classificationId", "classifierId")) '
                          'PARTITION BY LIST ("classifierId")' ),
                    reverse_sql=( 'DROP TABLE elasticc_brokerclassification' )
                ),
                migrations.RunSQL(
                    sql=( 'ALTER TABLE elasticc_brokerclassification '
                          'ATTACH PARTITION elasticc_brokerclassification_default DEFAULT' ),
                    reverse_sql=( 'ALTER TABLE elasticc_brokerclassification '
                                  'DETACH PARTITION elasticc_brokerclassification_default' )
                ),
                migrations.RunSQL(
                    sql=( 'ALTER TABLE "elasticc_brokerclassification" '
                          'ADD CONSTRAINT "unique_constarint_brokerclassification_partitionkey" '
                          'UNIQUE ("classifierId", "classificationId")' ),
                    reverse_sql=( 'ALTER TABLE "elasticc_brokerclassification" '
                                  'DROP CONSTRAINT unique_constarint_brokerclassification_partitionkey' )
                ),
                migrations.RunSQL(
                    sql=( 'ALTER TABLE "elasticc_brokerclassification" '
                          'ADD CONSTRAINT "elasticc_brokerclass_brokerMessageId_7741f498_fk_elasticc_" '
                          'FOREIGN KEY ("brokerMessageId") '
                          'REFERENCES "elasticc_brokermessage" ("brokerMessageId") '
                          'DEFERRABLE INITIALLY DEFERRED' ),
                    reverse_sql=( 'ALTER TABLE elasticc_brokerclassification '
                                  'DROP CONSTRAINT "elasticc_brokerclass_brokerMessageId_7741f498_fk_elasticc_"' )
                ),
                migrations.RunSQL(
                    sql=( 'CREATE INDEX "elasticc_brokerclassification_classId_05236c41" '
                          'ON "elasticc_brokerclassification" ("classId") ' ),
                    reverse_sql=( 'DROP INDEX "elasticc_brokerclassification_classId_05236c41"' )
                ),
                migrations.RunSQL(
                    sql=( 'CREATE INDEX "elasticc_brokerclassification_brokerMessageId_7741f498" '
                          'ON "elasticc_brokerclassification" ("brokerMessageId")' ),
                    reverse_sql=( 'DROP INDEX "elasticc_brokerclassification_brokerMessageId_7741f498"' )
                ),
            ],

            state_operations=[
                migrations.DeleteModel(
                    name='BrokerClassification'
                ),
                psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
                    name='BrokerClassification',
                    fields=[
                        ('classificationId', models.BigAutoField(primary_key=True, serialize=False)),
                        ('classifierId', models.BigIntegerField()),
                        ('classId', models.IntegerField(db_index=True)),
                        ('probability', models.FloatField()),
                        ('modified', models.DateTimeField(auto_now=True)),
                        ('dbMessage', models.ForeignKey(db_column='brokerMessageId', null=True,
                                                        on_delete=django.db.models.deletion.CASCADE,
                                                        to='elasticc.brokermessage')),
                    ],
                    partitioning_options={
                        'method': psqlextra.types.PostgresPartitioningMethod['LIST'],
                        'key': ['classifierId'],
                    },
                    bases=(psqlextra.models.partitioned.PostgresPartitionedModel,),
                    managers=[
                        ('objects', psqlextra.manager.manager.PostgresManager()),
                    ],
                ),
                psqlextra.backend.migrations.operations.add_default_partition.PostgresAddDefaultPartition(
                    model_name='BrokerClassification',
                    name='default',
                ),
                migrations.AddConstraint(
                    model_name='BrokerClassification',
                    constraint=models.UniqueConstraint(fields=('classifierId', 'classificationId'),
                                                       name='unique_constarint_brokerclassification_partitionkey'),
                ),
            ]
        ),
    ]