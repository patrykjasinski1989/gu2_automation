"""This module is not really used (at least not yet).
It will be used for getting data from ML database."""
import config
from db.db_helpers import connect


def ml_prod_connection():
    """Returns ML prod database connection."""
    return connect('RSW-DB', config.ML)


def get_order_data(con, msisdn):
    """Returns last order for a given MSISDN number."""
    cur = con.cursor()
    stmt = "select k.msisdn, k.idzleceniaom, z.id, z.status, z.datazmianystatusu " \
           "from ml.kontrakty k join ml.zlecenia z on z.id = k.idzlecenia " \
           "where k.msisdn = '{}' order by z.id desc".format(msisdn)
    cur.execute(stmt)
    row = cur.fetchone()
    if cur.rowcount == 1:
        result = {'msisdn': row[0], 'om_order_id': row[1], 'ml_id': row[2], 'status': row[3],
                  'last_status_change': row[4]}
    else:
        result = None
    cur.close()
    return result
