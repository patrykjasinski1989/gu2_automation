"""This module is used for communicating with ML STI database.
Also with ML PROD for WZMUKs, but that is just bad design..."""
import config
from db.db_helpers import execute_dml, connect


def ml_sti_connection():
    """Returns connection to ML STI database."""
    return connect('NIRSW2-DB', config.ML_STI)


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
