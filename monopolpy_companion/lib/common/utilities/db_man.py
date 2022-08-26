from lib.common.setup_env import db_path, os

def check_for(path=None):
    if path:
        path = path
    else:
        path = db_path

    if os.path.exists(os.path.abspath(path)):
        return True
    else:
        return False
