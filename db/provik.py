import config
from db.db_helpers import execute_dml, connect


def provik_connection():
    return connect('PROVIK-DB', config.PROVIK)


def get_latest_order(con, tel_order_id):
    query = """select ord_id, ord_state from (select * from om_order where ord_id in 
    (select bva_ref_order_id from om_bvalue where bva_value = '{}')
    and ord_state = 'COMPLETED' and ord_decomp_type = 'EXT_CREATION'
    order by ord_id desc)
    where rownum = 1
    """.format(tel_order_id)

    cur = con.cursor()
    cur.execute(query)
    row = cur.fetchone()
    cur.close()
    if cur.rowcount == 1:
        dict_row = {'ord_id': row[0], 'ord_state': row[1]}
    else:
        dict_row = None
    return dict_row


def is_gbill_out_for_order(con, ord_id):
    query = """select pgo_goal_name, pgo_state from om_process_goals 
    where pgo_ord_id = '{}' and pgo_goal_name = 'GBILL'""".format(ord_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount == 1


def has_gpreprov(con, ord_id):
    query = """select pgo_goal_name, pgo_state from om_process_goals 
    where pgo_ord_id = '{}' and pgo_goal_name = 'GPREPROV'""".format(ord_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount > 0


def cancel_order(con, ord_id):
    stmt = """update om_order set ord_state = 'CANCELLED' where ord_id = '{}'""".format(ord_id)
    execute_dml(con, stmt)
