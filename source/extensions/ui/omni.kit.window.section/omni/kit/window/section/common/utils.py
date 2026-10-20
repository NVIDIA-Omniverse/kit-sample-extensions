from pathlib import Path


def get_data_path(filename):
    ext_root_folder = Path(__file__).parent.parent.parent.parent.parent.parent
    return ext_root_folder.joinpath(f"data/{filename}").as_posix()


def Singleton(class_):
    """
    A singleton decorator.

    TODO: It's also available in other extensions. Do we have a utility extension where we can put the utilities
    like this?
    """
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance
