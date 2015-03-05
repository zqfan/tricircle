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

Other service should call Ceilometer API to post samples when resource created and deleted. There are some required fields, here is the minimum case:

curl -i -X POST http://10.67.148.221:8777/v2/resources -H "X-Auth-Token: $(keystone token-get | awk 'NR==5{print $4}')" -H 'Content-Type: application/json' -d '{"source": "nova", "resource_id": "123", "meter": [{"counter_name": "image", "counter_unit": "image", "counter_type": "gauge"}], "metadata": {"region": "regionOne", "cascaded_resource_id": "ff016a27-2126-4ac9-8c31-b4bd734e4892", "type": "nova.instance"}}'



Progress
========

* Alarm create API has been implemented. Only threshold alarm is supported. (2014-10-30)
* Alarm GET and DELETE API have been implemented. (2014-10-31)
* Resource CRUD have been implemented. (2014-02-28)
* Metric sample GET has been implemented. (2014-03-01)
* Metric statistics has been implemented. (2014-03-02)

