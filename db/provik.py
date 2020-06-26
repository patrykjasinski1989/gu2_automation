import config
from db.db_helpers import execute_dml, connect


def provik_connection():
    return connect('PROVIK-DB', config.PROVIK)
