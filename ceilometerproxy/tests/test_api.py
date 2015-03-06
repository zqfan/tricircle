#! /usr/bin/env python

from ceilometerclient import client as cm_client
from keystoneclient.v2_0 import client as ks_client
from oslo.config import cfg
import unittest

from ceilometer import service

cfg.CONF([], project='ceilometer')

CASCADING_CM_ENDPOINT = "http://127.0.0.1:8777"
CASCADED_CM_ENDPOINT = "http://10.67.148.224:8777"

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
    ceilometer_url=CASCADING_CM_ENDPOINT)

CASCADED_CM_CLIENT = cm_client.get_client(
    version=2,
    os_auth_token=TOKEN,
    ceilometer_url=CASCADED_CM_ENDPOINT)

class APITest(unittest.TestCase):
    SAMPLE = {
        "counter_name": "foo",
        "counter_type": "gauge",
        "counter_unit": "foo",
        "counter_volume": 0,
        "user_id": "123",
        "project_id": "456",
        "resource_id": "789",
        "resource_metadata": {
            "region": "regionOne",
            "cascaded_resource_id": "abc",
            "type": "nova.instance"
        }
    }

    def test_post_sample_create_resource(self):
        CASCADING_CM_CLIENT.samples.create(**self.SAMPLE)

    def test_alarm(self):
        pass

if __name__ == '__main__':
    unittest.main()
