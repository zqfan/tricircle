#! /usr/bin/env python

from __future__ import print_function
import json
import unittest

from ceilometerclient import client as cm_client
from ceilometerclient.openstack.common.apiclient import exceptions
from keystoneclient.v2_0 import client as ks_client
from oslo.config import cfg

from ceilometer import service  # noqa
from ceilometer import storage

cfg.CONF([], project='ceilometer')

CASCADING_CM_ENDPOINT = "https://metering.localdomain.com:8777"
CASCADED_CM_ENDPOINT = "https://metering.az2.dc21.domainname.com:443"
REGION = "regionOne"

TOKEN = ks_client.Client(
    username=cfg.CONF.service_credentials.os_username,
    password=cfg.CONF.service_credentials.os_password,
    tenant_id=cfg.CONF.service_credentials.os_tenant_id,
    tenant_name=cfg.CONF.service_credentials.os_tenant_name,
    cacert=cfg.CONF.service_credentials.os_cacert,
    auth_url=cfg.CONF.service_credentials.os_auth_url,
    region_name=cfg.CONF.service_credentials.os_region_name,
    insecure=cfg.CONF.service_credentials.insecure,).auth_token

CASCADING_CM_CLIENT = cm_client.get_client(
    version=2,
    os_auth_token=TOKEN,
    ceilometer_url=CASCADING_CM_ENDPOINT,
    insecure=cfg.CONF.service_credentials.insecure)

CASCADED_CM_CLIENT = cm_client.get_client(
    version=2,
    os_auth_token=TOKEN,
    ceilometer_url=CASCADED_CM_ENDPOINT,
    insecure=cfg.CONF.service_credentials.insecure)


class APITest(unittest.TestCase):

    def setUp(self):
        self.sample = {
            "counter_name": "foo",
            "counter_type": "gauge",
            "counter_unit": "foo",
            "counter_volume": 0,
            "user_id": "789",
            "project_id": "456",
            "resource_id": "123",
            "resource_metadata": {
                "region": REGION,
                "cascaded_resource_id": "abc",
                "type": "nova.instance"
            }
        }
        self.alarm_conn = storage.get_connection_from_config(
            cfg.CONF, purpose='alarm')
        self.conn = storage.get_connection_from_config(
            cfg.CONF, purpose='metering')
        # Danger! ensure dataset is empty
        #self.alarm_conn.db.alarm.remove({})
        #self.conn.db.resource.remove({})

    def tearDown(self):
        # Danger! ensure dataset is empty even test fails
        #self.alarm_conn.db.alarm.remove({})
        #self.conn.db.resource.remove({})
        pass

    def test_post_sample_create_delete_resource(self):
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        query = {
            "field": "resource_id",
            "value": "123"
        }
        resources = CASCADING_CM_CLIENT.resources.list(q=[query])
        self.assertEqual(1, len(resources))
        self.assertEqual("123", resources[0].resource_id)
        # meter links is enabled, so it should be several links
        self.assertTrue(len(resources[0].links) > 1)

        # remove it
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        resources = CASCADING_CM_CLIENT.resources.list(q=[query])
        self.assertEqual(0, len(resources))

    def test_get_samples_and_statistics_from_cascaded(self):
        samples = CASCADED_CM_CLIENT.samples.list(meter_name="instance",
                                                  limit=1)
        self.assertEqual(1, len(samples))
        resource_id = samples[0].resource_id
        self.sample['resource_metadata']['cascaded_resource_id'] = resource_id
        CASCADING_CM_CLIENT.samples.create(**self.sample)

        resource_query = {
            "field": "resource",
            "value": "123",
        }
        samples = CASCADING_CM_CLIENT.samples.list(meter_name="instance",
                                                   q=[resource_query],
                                                   limit=1)
        self.assertEqual(1, len(samples))
        self.assertEqual("123", samples[0].resource_id)
        statistics = CASCADING_CM_CLIENT.statistics.list(meter_name="instance",
                                                         q=[resource_query])
        self.assertEqual(1, len(statistics))

        # remove it
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        resources = CASCADING_CM_CLIENT.resources.list(q=[resource_query])
        self.assertEqual(0, len(resources))

    def test_single_resource_based_alarm(self):
        CASCADING_CM_CLIENT.samples.create(**self.sample)

        alarm = {
            "name": "alarm-test",
            "type": "threshold",
            "threshold_rule": {
                "threshold": 1,
                "meter_name": "instance",
                "query": [{
                    "field": "resource",
                    "value": "123",
                }]
            }
        }
        alarm = CASCADING_CM_CLIENT.alarms.create(**alarm)
        alarms = CASCADING_CM_CLIENT.alarms.list(q=[{"field": "name", "value": "alarm-test"}])
        self.assertEqual(1, len(alarms))
        self.assertEqual(alarm, alarms[0])
        self.assertEqual("123", alarm.threshold_rule['query'][0]['value'])

        # check cascaded node's alarm has internal resource id query
        alarms = list(self.alarm_conn.get_alarms(alarm_id=alarm.alarm_id))
        cascaded_alarm_id = (json.loads(alarms[0].description)
                             .get('cascaded_alarm_id'))
        cascaded_alarm = CASCADED_CM_CLIENT.alarms.get(cascaded_alarm_id)
        self.assertEqual("abc",
                         cascaded_alarm.threshold_rule['query'][0]['value'])

        # remove the alarm
        CASCADING_CM_CLIENT.alarms.delete(alarm.alarm_id)

        # remove the resource
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)

        # check cascaded node has delete corresponding alarm
        query = {
            "field": "alarm_id",
            "value": cascaded_alarm_id,
        }
        cascaded_alarms = CASCADED_CM_CLIENT.alarms.list(q=[query])
        self.assertEqual(0, len(cascaded_alarms))

    def test_resource_based_alarm_put(self):
        CASCADING_CM_CLIENT.samples.create(**self.sample)

        data = {
            "name": "alarm-test",
            "type": "threshold",
            "threshold_rule": {
                "threshold": 1,
                "meter_name": "instance",
                "query": [{
                    "field": "resource",
                    "value": "123",
                }]
            }
        }
        alarm = CASCADING_CM_CLIENT.alarms.create(**data)

        alarms = list(self.alarm_conn.get_alarms(alarm_id=alarm.alarm_id))
        cascaded_alarm_id = (json.loads(alarms[0].description)
                             .get('cascaded_alarm_id'))

        data['threshold_rule']['threshold'] = 100
        CASCADING_CM_CLIENT.alarms.update(alarm.alarm_id, **data)
        alarm = CASCADING_CM_CLIENT.alarms.get(alarm.alarm_id)
        c_alarm = CASCADED_CM_CLIENT.alarms.get(cascaded_alarm_id)
        self.assertEqual(100, alarm.threshold_rule['threshold'])
        self.assertEqual(100, c_alarm.threshold_rule['threshold'])

        # cannot change resource
        data['threshold_rule']['query'][0]['value'] = "456"
        self.assertRaises(exceptions.HttpError,
                          CASCADING_CM_CLIENT.alarms.update,
                          alarm.alarm_id, **data)
        self.assertEqual(alarm, CASCADING_CM_CLIENT.alarms.get(alarm.alarm_id))

        # remove the alarm
        CASCADING_CM_CLIENT.alarms.delete(alarm.alarm_id)

        # remove the resource
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)

    def test_az_based_alarm(self):
        data = {
            "name": "alarm-test",
            "type": "threshold",
            "threshold_rule": {
                "threshold": 1,
                "meter_name": "instance",
                "query": [{
                    "field": "metadata.metering.region",
                    "value": REGION,
                }]
            }
        }
        alarm = CASCADING_CM_CLIENT.alarms.create(**data)
        alarms = CASCADING_CM_CLIENT.alarms.list(q=[{"field": "name", "value": "alarm-test"}])
        self.assertEqual(1, len(alarms))
        self.assertEqual(alarm, alarms[0])

        # test alarm query has removed az info
        for query in alarm.threshold_rule['query']:
            self.assertNotEqual(query.field,
                                "metadata.metering.region")

        alarms = list(self.alarm_conn.get_alarms(alarm_id=alarm.alarm_id))
        cascaded_alarm_id = (json.loads(alarms[0].description)
                             .get('cascaded_alarm_id'))

        # test put alarm
        data['threshold_rule']['threshold'] = 100
        CASCADING_CM_CLIENT.alarms.update(alarm.alarm_id, **data)
        alarm = CASCADING_CM_CLIENT.alarms.get(alarm.alarm_id)
        c_alarm = CASCADED_CM_CLIENT.alarms.get(cascaded_alarm_id)
        self.assertEqual(100, alarm.threshold_rule['threshold'])
        self.assertEqual(100, c_alarm.threshold_rule['threshold'])

        # remove the alarm
        CASCADING_CM_CLIENT.alarms.delete(alarm.alarm_id)

        # check cascaded node has delete corresponding alarm
        query = {
            "field": "alarm_id",
            "value": cascaded_alarm_id,
        }
        cascaded_alarms = CASCADED_CM_CLIENT.alarms.list(q=[query])
        self.assertEqual(0, len(cascaded_alarms))

    def test_put_alarm_without_resource_nor_region(self):
        data = {
            "name": "alarm-test",
            "type": "threshold",
            "threshold_rule": {
                "threshold": 1,
                "meter_name": "instance",
                "query": [{
                    "field": "metadata.metering.region",
                    "value": REGION,
                }]
            }
        }
        alarm = CASCADING_CM_CLIENT.alarms.create(**data)
        data['threshold_rule']['threshold'] = 100
        data['threshold_rule']['query'] = []
        CASCADING_CM_CLIENT.alarms.update(alarm.alarm_id, **data)
        alarm = CASCADING_CM_CLIENT.alarms.get(alarm.alarm_id)
        self.assertEqual(100, alarm.threshold_rule['threshold'])
        self.assertEqual([], alarm.threshold_rule['query'])

        alarms = list(self.alarm_conn.get_alarms(alarm_id=alarm.alarm_id))
        cascaded_alarm_id = (json.loads(alarms[0].description)
                             .get('cascaded_alarm_id'))
        c_alarm = CASCADED_CM_CLIENT.alarms.get(cascaded_alarm_id)
        self.assertEqual(100, c_alarm.threshold_rule['threshold'])
        self.assertEqual([], c_alarm.threshold_rule['query'])
        

    def test_meter_list(self):
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        meters = CASCADING_CM_CLIENT.meters.list()
        self.assertNotEqual(0, len(meters))
        # remove the resource
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)

    def test_post_same_sample_multiple_times(self):
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        query = {
            "field": "resource_id",
            "value": "123"
        }
        resources = CASCADING_CM_CLIENT.resources.list(q=[query])
        self.assertEqual(1, len(resources))
        # remove the resource
        self.sample['resource_metadata'] = {}
        CASCADING_CM_CLIENT.samples.create(**self.sample)
        query = {
            "field": "resource_id",
            "value": "123"
        }
        resources = CASCADING_CM_CLIENT.resources.list(q=[query])
        self.assertEqual(0, len(resources))


if __name__ == '__main__':
    print("=" * 79)
    print("WARNING: MongoDB will be cleared after this test finish!!")
    print("Ensure you have at least one ACTIVE vm in cascaded node: %s" %
          CASCADED_CM_ENDPOINT)
    print("If there is a 500 error, check if resources have not been cleaned")
    print("=" * 79)
    suite = unittest.TestLoader().loadTestsFromTestCase(APITest)
    unittest.TextTestRunner(verbosity=2).run(suite)
