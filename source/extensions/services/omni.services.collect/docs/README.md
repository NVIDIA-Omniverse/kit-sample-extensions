# USD collections ervice.

The USD collection service helps with the batch processing of 'collection tasks' of USD files.
It uses the collect extension and provides an easy to use API to call into the service.

Once up and running it can be used from any process inside and outside of Kit via the service API

It supports collecting to local disks, Nucleus as well as remote storage solutions such as S3.
Additional storage solutions can be added by implementing the `_upload` function on a subclass of the BaseUploadCollector.

Settings:

- exts."omni.services.collect".concurrency
  How many copy/write and upload tasks to run in parallel.

- exts."omni.services.collect".collectors.aws.region
  AWS region to use. Defaults to None which means using the region defined in the [default] aws profile.

- exts."omni.services.collect".collectors.aws.profile
  AWS profile to use. Defaults to None which means using the [default] aws profile

- exts."omni.services.collect".collectors.aws.verify_ssl = ""
  Disabled by default == verify = True and use default ssl certs.
  Accepted arguments:
  - bool: True/False will enable/disable verifying SSL certificates
  - string: Path to a certificate bundle to use