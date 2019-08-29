"""This module is used for communicating with ML STI database.
Also with ML PROD for WZMUKs, but that is just bad design..."""
import cx_Oracle

import config
from db.db_helpers import execute_dml


def ml_sti_connection():
    """Returns connection to ML STI database."""
    dsn_tns = cx_Oracle.makedsn(config.ML_STI['ip'], config.ML_STI['port'], config.ML_STI['sid'])
    return cx_Oracle.connect(user=config.ML_STI['user'], password=config.ML_STI['password'], dsn=dsn_tns)


def delete_account(con, login, inc):
    """Disables access to ML for a given AD login."""
    stmt = """ UPDATE ml.bezp_kontroladostepu SET
                enabled = 'F',
                uwagi = '{} likwidacja konta'
                WHERE LOWER(login) = LOWER('{}') """.format(inc['inc'], login)
    return execute_dml(con, stmt)


def create_account(con, login, date, profile, inc):
    """Create a new access to ML for a given AD login."""
    stmt = """ INSERT INTO ml.bezp_kontroladostepu (
                login, expiration_date, enabled, profile, uwagi, id, bscs_dealer_id, bscs_dealer_code, bscs_code )
                SELECT '{login}', to_date('{date}', 'YYYY-MM-DD HH24:MI:SS'), 'T', '{profile}', '{inc} zalozenie konta',
                (SELECT MAX(id) + 1 FROM ml.bezp_kontroladostepu), -45800, 'KTML1', 'KTML1'
                FROM DUAL
                WHERE NOT EXISTS (SELECT 1 FROM ml.bezp_kontroladostepu WHERE enabled = 'T' 
                AND LOWER(login) = LOWER('{login}')) """.format(login=login, date=date, profile=profile, inc=inc)
    return execute_dml(con, stmt)


def recertify_account(con, login, date, profile, inc):
    """Modifies access data - access profile and account validity date"""
    stmt = """ UPDATE ml.bezp_kontroladostepu SET
                enabled = 'T',
                uwagi = '{inc} recertyfikacja',
                expiration_date = to_date('{date}', 'YYYY-MM-DD HH24:MI:SS'),
                profile = '{profile}'
                WHERE LOWER(login) = LOWER('{login}') """.format(login=login, date=date, profile=profile, inc=inc)
    return execute_dml(con, stmt)


if __name__ == '__main__':
    ML_STI = ml_sti_connection()
    print(ML_STI)
    ML_STI.close()
