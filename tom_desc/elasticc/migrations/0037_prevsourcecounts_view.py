# Generated by Django 4.1.2 on 2022-11-14 22:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('elasticc', '0036_alter_brokerclassification_classid'),
    ]

    operations = [
        migrations.RunSQL( """
CREATE MATERIALIZED VIEW elasticc_view_prevsourcecounts AS
SELECT subq."diaSourceId",subq."diaObjectId",subq."midPointTai",subq.ndetections,subq.mint,
       COUNT(fs."diaForcedSourceId") as nforced
FROM (
  SELECT s0."diaSourceId",s0."diaObjectId",s0."midPointTai",
         COUNT(s."diaSourceId") AS ndetections,
         MIN(s."midPointTai") AS mint
  FROM elasticc_diasource s0
  LEFT JOIN elasticc_diasource s
       ON s."diaObjectId"=s0."diaObjectId" AND s."midPointTai"<=s0."midPointTai"
  GROUP BY s0."diaSourceId",s0."diaObjectId",s0."midPointTai"
  ) subq
LEFT JOIN elasticc_diaforcedsource fs
   ON fs."diaObjectId"=subq."diaObjectId"
      AND fs."midPointTai"<subq."midPointTai"
      AND subq."midPointTai">(subq.mint+0.5)
        GROUP BY subq."diaSourceId",subq."diaObjectId",subq."midPointTai",subq.ndetections,subq.mint""" ),

        migrations.RunSQL( 'CREATE INDEX ON elasticc_view_prevsourcecounts ("diaSourceId")' ),
        migrations.RunSQL( 'CREATE INDEX ON elasticc_view_prevsourcecounts ("diaObjectId")' ),
        
        migrations.RunSQL( "GRANT SELECT ON elasticc_view_prevsourcecounts TO postgres_elasticc_admin_ro" )
    ]