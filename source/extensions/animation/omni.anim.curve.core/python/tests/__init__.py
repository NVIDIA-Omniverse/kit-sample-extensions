try:
    from .tests import *
except Exception as e:
    import carb

    carb.log_error("Import tests error: %s" % e)
