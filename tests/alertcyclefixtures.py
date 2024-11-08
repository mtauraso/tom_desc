# IMPORTANT -- running any tests that depend on fixtures in this file
# OTHER than alert_cycle_complete requires a completely fresh
# environment.  After any run of "pytest ...", if you want to run tests
# (e.g. in test_alert_cycle.py) that use these fixtures, you have to
# completely tear down and rebuild the docker compose environment.  This
# is because, as noted below, we can't easily clean up the kafka
# server's state, so on a rerun, the server state will be wrong.  (We
# also use that as a reason to be lazy and not clean up the database;
# see the long comment below.)

import sys
import os
import pathlib
import datetime
import time
import pytz
import random
import subprocess
import pytest

from pymongo import MongoClient

sys.path.insert( 0, "/tom_desc" )
os.environ["DJANGO_SETTINGS_MODULE"] = "tom_desc.settings"
import django
django.setup()

import elasticc2.models
import fastdb_dev.models
import tom_targets.models

from tom_client import TomClient
from msgconsumer import MsgConsumer

# NOTE -- in many of the fixtures below there are lots of tests that
# would normally be in the tests_* file that use the fixtures.  The
# reason they're here is because it's hard (impossible without a bunch
# of ugly hacks) to really clean up after these fixtures -- in
# particular, cleaning up the kafka server topic is something I can't
# just do here, but would have to do *on* the kafka server.  So, once
# some of the later fixtures have run, tests that depend only on earlier
# fixtures would start to fail.  The solution is to make all the
# fixtures session scoped, and to put the tests that have this
# hysteresis problem inside the fixtures, so they'll only be run once,
# and we can control the order in which the fixtures are run.  That will
# also then allow us to use these fixtures in more than one set of
# tests.

# Because of this, lots of fixtures don't bother cleaning up, even if
# they could.  In fact, they deliberately choose not to clean up,
# so that the database will be in the state it is at the end of the
# full alert cycle; the alert_cycle_complete fixture then detects that
# and runs the slow fixtures or not as necessary.

# Any tests that use these fixtures and are going to test actual numbers
# in the database should only depend on alert_cycle_complete.  Once all
# these fixtures have run (perhaps from an earlier test), the numbers
# that come out of earlier fixtures will no longer be right.  If any
# fixture other than alert_cycle_complete is run when the other fixtures
# have already been run once in a given docker compose environment, the
# database will be changed, and the fixtures will fail.

# The numbers in these tests are based on the SNANA files in the
# directory elasticc2_alert_test_data under tests, which should
# be unpacked from elasticc2_alert_test_data.tar.bz2.

class AlertCounter:
    def __init__( self ):
        self._test_alerts_exist_count = 0

    def handle_test_alerts_exist( self, msgs ):
        self._test_alerts_exist_count += len(msgs)


@pytest.fixture( scope="session" )
def alerts_300days( elasticc2_ppdb ):
    result = subprocess.run( [ "python", "manage.py", "send_elasticc2_alerts", "-d", "60578",
                               "-k", "kafka-server:9092",
                               "--wfd-topic", "alerts-wfd", "--ddf-full-topic", "alerts-ddf-full",
                               "--ddf-limited-topic", "alerts-ddf-limited",
                               "-s", "/tests/schema/elasticc.v0_9_1.alert.avsc",
                               "-r", "sending_alerts_runningfile", "--do" ],
                               cwd="/tom_desc", capture_output=True )
    sys.stderr.write( result.stderr.decode( 'utf-8' ) )
    assert result.returncode == 0

    consumer = MsgConsumer( 'kafka-server:9092', 'test_send_alerts', [ 'alerts-wfd', 'alerts-ddf-full' ],
                            '/tests/schema/elasticc.v0_9_1.alert.avsc',
                            consume_nmsgs=100 )
    counter = AlertCounter()
    consumer.poll_loop( counter.handle_test_alerts_exist, timeout=10, stopafter=datetime.timedelta(seconds=10) )
    # I don't understand why this is 546.  545 were sent.
    # The fake broker sees 545.
    assert counter._test_alerts_exist_count == 546
    consumer.close()

    yield True


@pytest.fixture( scope="session" )
def classifications_300days_exist( alerts_300days ):

    counter = AlertCounter()
    consumer = MsgConsumer( 'kafka-server:9092', 'test_classifications_exist', 'classifications',
                            '/tests/schema/elasticc.v0_9_1.brokerClassification.avsc',
                            consume_nmsgs=100 )
    consumer.reset_to_start( 'classifications' )

    # fake broker has a 10s sleep loop, so we can't
    # assume things will be there instantly; thus, the 16s timeout.

    consumer.poll_loop( counter.handle_test_alerts_exist, timeout=5,
                        stopafter=datetime.timedelta(seconds=16) )

    # This is 2x545
    assert counter._test_alerts_exist_count == 1090
    consumer.close()

    yield True


@pytest.fixture( scope="session" )
def classifications_300days_elasticc2_ingested( classifications_300days_exist ):
    # Have to have an additional sleep after the classifications exist,
    # because brokerpoll itself has a 10s sleep loop
    time.sleep( 11 )

    # Have to have these tests here rather than in the actual test_*
    # file because I can't clean up, and there is hysteresis.  Once
    # later fixtures have run, the tests below would fail, and these
    # fixtures may be used in more than one test.

    brkmsg = elasticc2.models.BrokerMessage
    cfer = elasticc2.models.BrokerClassifier
    bsid = elasticc2.models.BrokerSourceIds

    assert brkmsg.objects.count() == 1090
    assert cfer.objects.count() == 2
    assert bsid.objects.count() == 545

    numprobs = 0
    for msg in brkmsg.objects.all():
        assert len(msg.classid) == len(msg.probability)
        numprobs += len(msg.classid)

    # 545 from NugentClassifier plus 20*545 for RandomSNType
    assert numprobs == 11445

    # TODO : check that the data is identical for
    # corresponding entries in the two cassbroker
    # tables

    assert ( set( [ i.classifiername for i in cfer.objects.all() ] )
             == set( [ "NugentClassifier", "RandomSNType" ] ) )

    yield True


@pytest.fixture( scope="session" )
def classifications_300days_fastdb_dev_ingested( classifications_300days_exist ):
    # Have to have an additional sleep after the classifications exist,
    # because brokerpoll itself has a 10s sleep loop
    time.sleep( 11 )

    # Have to have these tests here rather than in the actual test_*
    # file because I can't clean up, and there is hysteresis.  Once
    # later fixtures have run, the tests below would fail, and these
    # fixtures may be used in more than one test.

    host = os.getenv( 'MONGOHOST' )
    username = os.getenv( 'MONGODB_ALERT_READER' )
    password = os.getenv( 'MONGODB_ALERT_READER_PASSWORD' )
    client = MongoClient( f"mongodb://{username}:{password}@{host}:27017/?authSource=alerts" )
    db = client.alerts

    assert 'fakebroker' in db.list_collection_names()

    coll = db.fakebroker
    assert coll.count_documents({}) == 1090

    numprobs = 0
    for msg in coll.find():
        msg = msg['msg']
        assert msg['brokerName'] == 'FakeBroker'
        assert msg['classifierName'] in [ 'RandomSNType', 'NugentClassifier' ]
        if msg['classifierName'] == 'NugentClassifier':
            assert len( msg['classifications'] ) == 1
            assert msg['classifications'][0]['classId'] == 2222
            assert msg['classifications'][0]['probability'] == 1.0
        numprobs += len( msg['classifications'] )
    assert numprobs == 11445

    yield True

@pytest.fixture( scope="session" )
def update_elasticc2_diasource_300days( classifications_300days_elasticc2_ingested ):
    result = subprocess.run( [ "python", "manage.py", "update_elasticc2_sources" ],
                             cwd="/tom_desc", capture_output=True )
    assert result.returncode == 0

    # Have to have tests here because of hysteresis (search for that word above)
    obj = elasticc2.models.DiaObject
    src = elasticc2.models.DiaSource
    frced = elasticc2.models.DiaForcedSource
    targ = tom_targets.models.Target
    ooft = elasticc2.models.DiaObjectOfTarget
    bsid = elasticc2.models.BrokerSourceIds

    assert bsid.objects.count() == 0
    assert obj.objects.count() == 102
    # TODO -- put these next two lines back in once we start doing this thing again
    # assert ooft.objects.count() == obj.objects.count()
    # assert targ.objects.count() == obj.objects.count()
    assert src.objects.count() == 545
    assert frced.objects.count() == 4242

    yield True


@pytest.fixture( scope="session" )
def update_fastdb_dev_diasource_300days( classifications_300days_fastdb_dev_ingested ):
    result = subprocess.run( [ "python", "manage.py", "load_fastdb",
                               "--pv", "test_pv", "--snapshot", "test_ss",
                               "--tag", "test_ss_tag",
                               "--brokers", "fakebroker" ],
                             cwd="/tom_desc",
                             capture_output=True )
    assert result.returncode == 0

    lut = fastdb_dev.models.LastUpdateTime
    obj = fastdb_dev.models.DiaObject
    src = fastdb_dev.models.DiaSource
    frced = fastdb_dev.models.DiaForcedSource
    cfer = fastdb_dev.models.BrokerClassifier
    cification = fastdb_dev.models.BrokerClassification
    pver = fastdb_dev.models.ProcessingVersions
    ss = fastdb_dev.models.Snapshots
    dspvss = fastdb_dev.models.DStoPVtoSS
    dfspvss = fastdb_dev.models.DFStoPVtoSS

    assert lut.objects.count() == 1
    assert lut.objects.first().last_update_time > datetime.datetime.fromtimestamp( 0, tz=datetime.timezone.utc )
    assert lut.objects.first().last_update_time < datetime.datetime.now( tz=datetime.timezone.utc )

    # TODO : right now, load_fastdb.py imports the future -- that is, it imports
    #   the full ForcedSource lightcure for an object for which we got a source
    #   the first time that source is seen, and never looks at forcedsources
    #   again.  Update the tests numbers if/when it simulates not knowing the
    #   future.
    # (Really, we should probably creat a whole separate simulated PPDB server with
    #  an interface that will look something like the real PPDB interface... when
    #  we actually know what that is.)

    assert obj.objects.count() == 102
    assert src.objects.count() == 545
    assert frced.objects.count() == 15760   # 4242
    assert cfer.objects.count() == 2
    # assert cification.objects.count() == 831  # ???? WHy is this not 545 * 2 ?   LOOK INTO THIS
    #                                           # ---> seems to be non-deterministic!
    # TODO : pver, ss, dpvss, dfspvss

    yield True

@pytest.fixture( scope="session" )
def alerts_100daysmore( alerts_300days ):
    # This will send alerts up through mjd 60676.  Why not 60678, since the previous
    #   sent through 60578?  There were no alerts between 60675 and 60679, so the last
    #   alert sent will have been a source from mjd 60675.  That's what the 100 days
    #   are added to.
    # This is an additional 105 alerts, for a total of 650 (coming from 131 objects).
    result = subprocess.run( [ "python", "manage.py", "send_elasticc2_alerts", "-a", "100",
                               "-k", "kafka-server:9092",
                               "--wfd-topic", "alerts-wfd", "--ddf-full-topic", "alerts-ddf-full",
                               "--ddf-limited-topic", "alerts-ddf-limited",
                               "-s", "/tests/schema/elasticc.v0_9_1.alert.avsc",
                               "-r", "sending_alerts_runningfile", "--do" ],
                               cwd="/tom_desc", capture_output=True )
    sys.stderr.write( result.stderr.decode( 'utf-8' ) )
    assert result.returncode == 0

    yield True

    # Same issue as alerts_300days about not cleaning up

@pytest.fixture( scope="session" )
def classifications_100daysmore_elasticc2_ingested( alerts_100daysmore ):
    # This time we need to allow for both the 10s sleep cycle timeout of
    # brokerpoll and fakebroker (since we're not checking
    # classifications exist separately from ingested)
    time.sleep( 22 )

    # Tests here because of hysteresis

    brkmsg = elasticc2.models.BrokerMessage
    cfer = elasticc2.models.BrokerClassifier

    # 650 total alerts times 2 classifiers = 1300 broker messages
    assert len( brkmsg.objects.all() ) == 1300
    assert cfer.objects.count() == 2
    assert len( cfer.objects.all() ) == 2

    numprobs = 0
    for msg in brkmsg.objects.all():
        assert len(msg.classid) == len(msg.probability)
        numprobs += len(msg.classid)
    # 650 from NugentClassifier plus 20*650 for RandomSNType
    assert numprobs == 13650

    assert ( set( [ i.classifiername for i in cfer.objects.all() ] )
             == set( [ "NugentClassifier", "RandomSNType" ] ) )

    yield True


@pytest.fixture( scope="session" )
def classifications_100daysmore_fastdb_dev_ingested( alerts_100daysmore ):
    # This time we need to allow for both the 10s sleep cycle timeout of
    # brokerpoll and fakebroker (since we're not checking
    # classifications exist separately from ingested)
    time.sleep( 22 )

    # Tests here because of hysteresis

    host = os.getenv( 'MONGOHOST' )
    username = os.getenv( 'MONGODB_ALERT_READER' )
    password = os.getenv( 'MONGODB_ALERT_READER_PASSWORD' )
    client = MongoClient( f"mongodb://{username}:{password}@{host}:27017/?authSource=alerts" )
    db = client.alerts

    assert 'fakebroker' in db.list_collection_names()

    coll = db.fakebroker
    assert coll.count_documents({}) == 1300

    numprobs = 0
    for msg in coll.find():
        msg = msg['msg']
        assert msg['brokerName'] == 'FakeBroker'
        assert msg['classifierName'] in [ 'RandomSNType', 'NugentClassifier' ]
        if msg['classifierName'] == 'NugentClassifier':
            assert len( msg['classifications'] ) == 1
            assert msg['classifications'][0]['classId'] == 2222
            assert msg['classifications'][0]['probability'] == 1.0
        numprobs += len( msg['classifications'] )
    assert numprobs == 13650

    yield True


@pytest.fixture( scope="session" )
def update_elasticc2_diasource_100daysmore( classifications_100daysmore_elasticc2_ingested ):
    result = subprocess.run( [ "python", "manage.py", "update_elasticc2_sources" ],
                             cwd="/tom_desc", capture_output=True )
    assert result.returncode == 0

    obj = elasticc2.models.DiaObject
    src = elasticc2.models.DiaSource
    frced = elasticc2.models.DiaForcedSource
    targ = tom_targets.models.Target
    ooft = elasticc2.models.DiaObjectOfTarget
    bsid = elasticc2.models.BrokerSourceIds

    assert bsid.objects.count() == 0
    assert obj.objects.count() == 131
    # TODO: put these next two lines back in once we start doing this again
    # assert ooft.objects.count() == obj.objects.count()
    # assert targ.objects.count() == obj.objects.count()
    assert src.objects.count() == 650
    assert frced.objects.count() == 5765

    yield True


@pytest.fixture( scope="session" )
def update_fastdb_dev_diasource_100daysmore( classifications_100daysmore_fastdb_dev_ingested ):
    # SEE COMMENTS IN update_fastdb_dev_diasource_300days

    result = subprocess.run( [ "python", "manage.py", "load_fastdb",
                               "--pv", "test_pv", "--snapshot", "test_ss",
                               "--tag", "test_ss_tag",
                               "--brokers", "fakebroker" ],
                             cwd="/tom_desc",
                             capture_output=True )
    assert result.returncode == 0

    lut = fastdb_dev.models.LastUpdateTime
    obj = fastdb_dev.models.DiaObject
    src = fastdb_dev.models.DiaSource
    frced = fastdb_dev.models.DiaForcedSource
    cfer = fastdb_dev.models.BrokerClassifier
    cification = fastdb_dev.models.BrokerClassification
    pver = fastdb_dev.models.ProcessingVersions
    ss = fastdb_dev.models.Snapshots
    dspvss = fastdb_dev.models.DStoPVtoSS
    dfspvss = fastdb_dev.models.DFStoPVtoSS

    assert lut.objects.count() == 1
    assert lut.objects.first().last_update_time > datetime.datetime.fromtimestamp( 0, tz=datetime.timezone.utc )
    assert lut.objects.first().last_update_time < datetime.datetime.now( tz=datetime.timezone.utc )

    # TODO : right now, load_fastdb.py imports the future -- that is, it imports
    #   the full ForcedSource lightcure for an object for which we got a source
    #   the first time that source is seen, and never looks at forcedsources
    #   again.  Update the tests numbers if/when it simulates not knowing the
    #   future.
    # (Really, we should probably creat a whole separate simulated PPDB server with
    #  an interface that will look something like the real PPDB interface... when
    #  we actually know what that is.)

    assert obj.objects.count() == 131
    assert src.objects.count() == 650
    assert frced.objects.count() == 20834   # 5765
    assert cfer.objects.count() == 2
    # assert cification.objects.count() == ...  # ???? WHy is this not 650 * 2 ?   LOOK INTO THIS
    # TODO : pver, ss, dpvss, dfspvss

    yield True

@pytest.fixture( scope="session" )
def api_classify_existing_alerts( alerts_100daysmore, apibroker_client ):
    result = subprocess.run( [ "python", "apiclassifier.py", "--source", "kafka-server:9092",
                               "-t", "alerts-wfd", "alerts-ddf-full",
                               "-g", "apibroker", "-u", "apibroker", "-p", "testing", "-s", "2",
                               "-a", "/tests/schema/elasticc.v0_9_1.alert.avsc",
                               "-b", "/tests/schema/elasticc.v0_9_1.brokerClassification.avsc"],
                             cwd="/tests", capture_output=True )
    sys.stderr.write( result.stderr.decode( 'utf-8' ) )
    assert result.returncode == 0

    yield True

@pytest.fixture( scope="module" )
def random_broker_classifications():
    brokers = {
        'rbc_test1': {
            '1.0': {
                'classifiertest1': [ '1.0' ],
                'classifiertest2': [ '1.0' ]
            }
        },
        'rbc_test2': {
            '3.5': {
                'testing1': [ '42' ],
                'testing2': [ '23' ]
            }
        }
    }

    minsrc = 10
    maxsrc = 20
    mincls = 1
    maxcls = 20

    msgs = []
    for brokername, brokerspec in brokers.items():
        for brokerversion, versionspec in brokerspec.items():
            for classifiername, clsspec in versionspec.items():
                for classifierparams in clsspec:
                    nsrcs = random.randint( minsrc, maxsrc )
                    for src in range(nsrcs):
                        ncls = random.randint( mincls, maxcls )
                        probleft = 1.0
                        classes = []
                        probs = []
                        for cls in range( ncls ):
                            classes.append( cls )
                            prob = random.random() * probleft
                            probleft -= prob
                            probs.append( prob )
                        classes.append( ncls )
                        probs.append( probleft )

                        msgs.append( { 'sourceid': src,
                                       'brokername': brokername,
                                       'alertid': src,
                                       'elasticcpublishtimestamp': datetime.datetime.now( tz=pytz.utc ),
                                       'brokeringesttimestamp': datetime.datetime.now( tz=pytz.utc ),
                                       'brokerversion': brokerversion,
                                       'classifiername': classifiername,
                                       'classifierparams': classifierparams,
                                       'classid': classes,
                                       'probability': probs } )

    yield msgs


@pytest.fixture( scope="session" )
def alert_cycle_complete( request, tomclient ):
    res = tomclient.post( 'db/runsqlquery/',
                          json={ 'query': 'SELECT COUNT(*) AS count FROM elasticc2_brokermessage' } )
    rows = res.json()[ 'rows' ]
    if rows[0]['count'] == 0:
        request.getfixturevalue( "update_elasticc2_diasource_100daysmore" )
        request.getfixturevalue( "update_fastdb_dev_diasource_100daysmore" )
        request.getfixturevalue( "api_classify_existing_alerts" )

    yield True


__all__ = [ 'alerts_300days',
            'classifications_300days_exist',
            'classifications_300days_elasticc2_ingested',
            'classifications_300days_fastdb_dev_ingested',
            'update_elasticc2_diasource_300days',
            'update_fastdb_dev_diasource_300days',
            'alerts_100daysmore',
            'classifications_100daysmore_elasticc2_ingested',
            'classifications_100daysmore_fastdb_dev_ingested',
            'update_fastdb_dev_diasource_100daysmore',
            'api_classify_existing_alerts',
            'alert_cycle_complete' ]
