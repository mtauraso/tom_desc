# Generated by Django 4.0.6 on 2022-08-19 17:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0038_partition_brokerclassification'),
    ]

    operations = [
        migrations.RunSQL( "DROP VIEW elasticc_view_sourceclassifications" ),
        migrations.RunSQL( """
CREATE VIEW elasticc_view_sourceclassifications AS
  SELECT cfer."classifierId",cfer."brokerName", cfer."brokerVersion",
         cfer."classifierName", cfer."classifierParams",
         c."classId", c.probability,
         s."diaSourceId", s."diaObjectId",
         t.gentype, cm."classId" AS "trueClassId",
         a."alertId",
         m."brokerMessageId",
         a."alertSentTimestamp",
         m."elasticcPublishTimestamp",
         m."brokerIngestTimestamp",
         m."msgHdrTimestamp",
         m."descIngestTimestamp"
  FROM elasticc_brokermessage m
  INNER JOIN elasticc_brokerclassification c ON m."brokerMessageId"=c."brokerMessageId"
  INNER JOIN elasticc_brokerclassifier cfer ON c."classifierId"=cfer."classifierId"
  INNER JOIN elasticc_diasource s ON s."diaSourceId"=m."diaSourceId"
  INNER JOIN elasticc_diaalert a ON m."alertId"=a."alertId"
  INNER JOIN elasticc_diaobjecttruth t ON t."diaObjectId"=s."diaObjectId"
  INNER JOIN elasticc_gentypeofclassid cm ON t.gentype=cm.gentype
""" ),
        migrations.RunSQL( "GRANT SELECT ON elasticc_view_sourceclassifications TO postgres_elasticc_admin_ro" )
    ]