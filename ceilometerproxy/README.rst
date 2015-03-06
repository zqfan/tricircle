OpenStack Ceilometer Proxy
==========================

Key Modules
-----------

* ceilometer/api/controller/v2.py
* ceilometer/storage/impl_mongodb.py

Requirements
------------

* openstack-ceilometer-api-juno has been installed
* mongodb has been installed

Installation
------------

We provide two ways to install the Cinder-Proxy code. In this section, we will guide you through installing the Cinder-Proxy with the minimum configuration.

* **Note:**

    - Make sure you have an existing installation of **Openstack Juno**.
    - We recommend that you Do backup at least the following files before installation, because they are to be overwritten or modified:
        $CEILOMETER_CONFIG_PARENT_DIR/ceilometer.conf
        (replace the $... with actual directory names.)

* **Manual Installation**

    - Make sure you have performed backups properly.

    - Navigate to the local repository and copy the contents in 'ceilometer' sub-directory to the corresponding places in existing cinder, e.g.
      ```cp -r $LOCAL_REPOSITORY_DIR/ceilometer $CEILOMETER_PARENT_DIR```
      (replace the $... with actual directory name.)

    - Restart the ceilometer-api.
      ```service openstack-ceilometer-api restart```

    - Done. The ceilometer-api should be working with a demo configuration.


Functionalities
===============

1. Alarm CRUD. (List of alarm will not be supported yet. This aims to implement Heat autoscaling feature)


Details
-------

* API will not support admin user access in cascading level, and capabilities are limited for normal users.
* Metering API only support single resource based for normal user


Implementation
==============

Details
-------

* Each OpenStack service should call Ceilometer API to post samples when resource created and deleted, cascaded UUID and region information should be contained in sample 'resource_metadata' field. If post request doesn't contain such information, it means it is a resource delete operation. We should change the default behavior of store data via pipeline->AMQP->database, directly push data to database instead of via AMQP.
* Ceilometer gets cascaded UUID from resource table, and uses it to query samples or create alarm in cascaded level.
* Alarm will be saved in alarm table, but will proxy to cascaded level when request a specific alarm. Get all alarms is supported but their state and some other field may not be correct, currently we don't sync state with cascaded level.

Interavtive
-----------

Other service should call Ceilometer API to post samples when resource created and deleted.

To avoid couple with Ceilometer, you can use a configure option to indicates whether Ceilometer is enabled. For example::

    def __init__(self, xxx):
        ...
        self.cm_client = None
        if cfg.CONF.ceilometer_enabled:
            self.cm_client = ceilometerclient.client.get_client(2, xxx)

    def vm_create(self, xxx):
        ...
        if self.cm_client:
            sample = {
                "counter_name": "foo", # can be anything
                "counter_type": "gauge", # hard-coded, can be one of gauge, delta, cumulative
                "counter_unit": "foo", # can be anything
                "couter_volume": 0, # can be any float value
                "user_id": vm.user_id, # should be the created vm's user_id
                "project_id": vm.project_id, # should be the created vm's project_id
                "resource_id": vm.uuid, # should be the created vm's uuid
                "resource_metadata": {
                    "region": "regionOne", # which region this vm belongs to
                    "cascaded_resource_id": "bar", # the uuid of this vm in cascaded level
                    "type": "nova.instance", # the type of this resource, see all types in etc/ceilometer/type2meters.json
                }
            self.cm_client.samples.create(**sample)
        ...

    def vm_delete(self, xxx):
        ...
        if self.cm_client:
            sample = {
                "counter_name": "foo", # can be anything
                "counter_type": "gauge", # hard-coded, can be one of gauge, delta, cumulative
                "counter_unit": "foo", # can be anything
                "couter_volume": 0, # can be any float value
                "user_id": vm.user_id, # should be the created vm's user_id
                "project_id": vm.project_id, # should be the created vm's project_id
                "resource_id": vm.uuid, # should be the created vm's uuid
                "resource_metadata": {} # empty resource metadata indicates resource delete operation
            self.cm_client.samples.create(**sample)
        ...

The above example shows all the required fields, when resource_metadata is empty, it means this resource is deleted. Here is the equal curl presentation:

curl -i -X POST 'http://10.67.148.221:8777/v2/meters/instance' -H "X-Auth-Token: $(keystone token-get | awk 'NR==5{print $4}')" -H 'Content-Type: application/json' -d '[{"counter_name": "instance", "counter_type": "gauge", "counter_unit": "instance", "counter_volume": 1.0, "user_id": "d22a404f68c4485bb9193f7a1e17c74c", "resource_id": "df422bf5-10f3-4ecb-a9e3-f1dea761052a", "project_id": "db1921917d8543b1ba7ff9b1f1df6081", "resource_metadata": {"region": "regionOne", "cascaded_resource_id": "ff016a27-2126-4ac9-8c31-b4bd734e4892", "type": "nova.instance"}}]'

curl -i -X POST 'http://10.67.148.221:8777/v2/meters/instance' -H "X-Auth-Token: $(keystone token-get | awk 'NR==5{print $4}')" -H 'Content-Type: application/json' -d '[{"counter_name": "instance", "counter_type": "gauge", "counter_unit": "instance", "counter_volume": 1.0, "user_id": "d22a404f68c4485bb9193f7a1e17c74c", "resource_id": "df422bf5-10f3-4ecb-a9e3-f1dea761052a", "project_id": "db1921917d8543b1ba7ff9b1f1df6081", "resource_metadata": {}}]'

here is another way which directly post or delete a resource, this API has no CLI support and may be removed:

curl -i -X POST http://10.67.148.221:8777/v2/resources -H "X-Auth-Token: $(keystone token-get | awk 'NR==5{print $4}')" -H 'Content-Type: application/json' -d '{"source": "nova", "resource_id": "123", "meter": [{"counter_name": "image", "counter_unit": "image", "counter_type": "gauge"}], "metadata": {"region": "regionOne", "cascaded_resource_id": "ff016a27-2126-4ac9-8c31-b4bd734e4892", "type": "nova.instance"}}'

curl -i -X DELETE http://10.67.148.221:8777/v2/resources/123 -H "X-Auth-Token: $(keystone token-get | awk 'NR==5{print $4}')" -H 'Content-Type: application/json'

Progress
========

* Alarm create API has been implemented. Only threshold alarm is supported. (2014-10-30)
* Alarm GET and DELETE API have been implemented. (2014-10-31)
* Resource CRUD have been implemented. (2014-02-28)
* Metric sample GET has been implemented. (2014-03-01)
* Metric statistics has been implemented. (2014-03-02)

