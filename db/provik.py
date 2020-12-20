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
    where pgo_ord_id = '{}' and pgo_goal_name = 'GBILL' and pgo_state = 'OUT'""".format(ord_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount == 1


def get_pgo_id(con, ord_id, pgo_goal_name):
    query = """select pgo+id from om_process_goals 
    where pgo_ord_id = '{}' and pgo_goal_name = '{}'""".format(ord_id, pgo_goal_name)
    cur = con.cursor()
    cur.execute(query)
    row = cur.fetchone()
    cur.close()
    return row[0]


def has_gpreprov(con, ord_id):
    query = """select pgo_goal_name, pgo_state from om_process_goals 
        where pgo_ord_id = '{}' and pgo_goal_name = 'GPREPROV'""".format(ord_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount > 0


def is_geqret_processing(con, ord_id):
    query = """select pgo_goal_name, pgo_state from om_process_goals 
        where pgo_ord_id = '{}' and pgo_goal_name = 'GEQRET' and pgo_state = 'PROCESSING'""".format(ord_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount > 0


def cancel_order(con, ord_id):
    stmt = """update om_order set ord_state = 'CANCELLED' where ord_id = '{}'""".format(ord_id)
    execute_dml(con, stmt)


def has_pbi184471_error(con, tel_order_id):
    query = """select b.bva_value, o.ord_id, res.*
        from om_bvalue b, om_order o, om_process_goals g, om_cm_message req, om_cm_async_response res
        where o.ord_id = g.pgo_ord_id and b.bva_ref_order_id = o.ord_id 
        and g.pgo_id = req.cmr_pgo_id and req.cmr_id = res.cma_cmr_id
        and o.ord_state not in ('CANCELLED', 'COMPLETED') 
        and g.pgo_goal_name = 'GACCESS' and g.pgo_state not in ('OUT', 'SKIP')
        and res.cma_document_type = 'tp.esa.network.orderhandling.feasibilitystudy.doc:docFeasibilityStudyResultRequest'
        and (res.cma_data like '%PBI000000184471%'
        or res.cma_data like '%pola TYPE w rekordzie DOCUMENT_LINE%')
        and bva_value='{}'""".format(tel_order_id)
    cur = con.cursor()
    cur.execute(query)
    cur.fetchall()
    cur.close()
    return cur.rowcount > 0
