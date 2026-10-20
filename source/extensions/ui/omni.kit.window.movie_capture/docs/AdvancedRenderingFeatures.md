# Support for advanced rendering features

## About

This document provides information about advanced rendering features, which can be enabled for tasks submitted to Farm instances. If the selected Farm Queue instance advertizes its support for a know set of features, the Movie Capture extension can expose additional features allowing additional automation and batch features for remote workflows.

## Expected Farm Queue settings

When selecting a Farm Queue instance where rendering tasks will be submitted, as query is sent to the Farm Queue, probing it for the features it supports.

Some of the additional features which can be enabled on the client-side include:
 * Allowing Users to specify a list of additional extensions to be enabled on the Farm Agents processing tasks, in case rendering requires specific extensions which may not be included by default in their package.
 * Allowing Users to specify a list of extensions registries in which additional extensions can be searched.
 * etc.

The request is routed to the `/queue/settings` endpoint of the Farm Queue, which can be configured to respond with the following schema in order to enable additional features in the Movie Capture panel:

```json
{
    "advanced_rendering_features": {
        "ui_should_upload": true, // Boolean flag.
        "skip_upload_to_s3": true, // Boolean flag.
        "task_extensions": true, // Boolean flag.
        "task_registries": true, // Boolean flag.
        "generate_shader_cache": false, // Boolean flag.
        "farm_utilities_server": "https://utilities.farm.url", // URL of a Utilities Farm.
        "ingress_bucket": "ingress-bucket-name", // Name of the ingress storage bucket.
        "ingress_bucket_url": "https://ingress.bucket.url", // URL of the ingress storage bucket.
        "egress_bucket": "egress-bucket-name", // Name of the egress storage bucket.
        "egress_archive_bucket": "archive-bucket-name", // Name of the egress archive bucket.
        "aws_profile": "ProfileName" // Name of the AWS profile.
    }
}
```
