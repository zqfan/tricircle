Functionalities
===============

1. Alarm create, update, delete, get. List of alarm will not be supported yet. This aims to implement Heat autoscaling feature

Details
=======

1. API will not support admin user access in cascading level, and capabilities are limited for normal users.
2. API will get limited regions from accessing project, and collect data from those region in cascaded level. If any of them fail, the request in cascading level will return fail (retry can be added if possible).
3. Each OpenStack service should call Ceilometer API to post samples when resource created and deleted, cascaded UUID and region information should be contained in sample 'resource_metadata' field. If post request doesn't contain such information, it means it is a resource delete operation. We should change the default behavior of store data via pipeline->AMQP->database, directly push data to database instead of via AMQP.
4. Ceilometer gets cascaded UUID from resource table, and uses it to create alarm in cascaded level.
5. Alarm will be saved as a resource too, so it will be in meter too, which will be a new non-existent meter: alarm.

Progress
========

1. Alarm create API has been implemented. Only threshold alarm is supported. (2014-10-30)
2. Alarm GET and DELETE API have been implemented. (2014-10-31)


