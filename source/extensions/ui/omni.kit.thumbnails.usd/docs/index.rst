omni.kit.thumbnails.usd: Thumbnail Generator
#############################################

USD Thumbnail generation.
=========================

Thumbnails are generated for USD files as the file is being save when this extension is enabled.
When the USD file is hosted on omniverse the thumbnails will be uploaded to Omniverse otherwise thumbnails are stored locally.


MDL Thumbnail generation.
=========================

From within the Content browser, use the context menu to request the generation of a thumbnail.
The rendering of the thumbnail is done remotely. This means that only MDL files stored on Omniverse are supported.

This requires the MDL Preview service to be deployed. The location of the service can be set via configuration:
--exts/omni.kit.thumbnail_generator/mdl_server="http://<server>"
