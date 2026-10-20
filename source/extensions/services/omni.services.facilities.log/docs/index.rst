Kit services log facility
#########################

The log facility abstracts away the implementation detail of the logging system used.
By default a ``CarbLogFacility`` is available which conforms to python's logging implementation.

Other log implementations can be added and can be swapped in transparently if other logging systems are preferred.

.. automodule:: omni.services.facilities.log
    :platform: windows-x86_64, linux-x86_64
    :members:
    :private-members:
    :special-members:
    :undoc-members:
    :show-inheritance:
    :imported-members:
    :exclude-members: contextmanager
