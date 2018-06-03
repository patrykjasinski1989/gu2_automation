# -*- coding: utf-8 -*-
import cx_Oracle

import config


def nra_connection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.nra['user'], config.nra['password'], config.nra['server']))


def get_sim_status(con, sim):
    cur = con.cursor()
    stmt = """
        select sim, plcode_bscs, plcode_nra, status_bscs, status_nra, imsi, p_plcode, p_status, hlrid_bscs,
        hlrid_nra, dealer_bscs, dealer_nra, d_status_bscs d_bscs, d_status_nra d_nra,
        nvl2(last_status, last_status||'->'||status_nra||' ('||to_char(do, 'yyyy-mm-dd hh24:mi')||' by '||
        nvl(user_mod, '?')||')', 'no history') last_sim_status_mod
        from (select sm.sm_serialnum sim, sm.plcode plcode_bscs, s.plcode plcode_nra, sm.sm_status status_bscs, 
        k.status status_nra,
        p.port_num imsi, p.plcode p_plcode, port_status p_status, m.hlrid hlrid_bscs, k.hlr_id hlrid_nra, 
        sm.dealer_id dealer_BSCS, K.DEALER_ID dealer_nra, d.cstype d_status_bscs, p.status d_status_nra,
        h.do, h.status last_status, h.data_mod, h.user_mod
        from port@bscs_nra p, storage_medium@bscs_nra sm, mpdhltab@bscs_nra m, karty_sim k, slo_plcode_lista s, 
        karty_sim_status_hist h, platnicy p, customer_all@bscs_nra d
        where p.sm_id = sm.sm_id and p.hlcode = m.hlcode and sm.sm_serialnum = k.sim 
        and k.id_slo_plcode = s.id_slo_plcode and sm.dealer_id = d.customer_id(+) and k.dealer_id = p.platnik_id(+)
        and s.czy_glowny = 'T' and to_char(k.sim) = h.sim_no(+)
        and sm_serialnum in ('{0}')
        order by od desc) where rownum = 1
    """.format(sim)
    cur.execute(stmt)
    sim_status = cur.fetchone()
    cur.close()
    if sim_status is not None:
        result = {'status_bscs': sim_status[3], 'status_nra': sim_status[4], 'imsi': sim_status[5]}
    else:
        result = {}
    return result


def set_sim_status_nra(con, sim, status):
    cur = con.cursor()
    stmt = """
        update karty_sim s
        set S.STATUS = '{1}'
        where sim in ('{0}')
    """.format(sim, status)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    return cur.rowcount


def set_sim_status_bscs(con, sim, status):
    cur = con.cursor()
    stmt = """
        update storage_medium@bscs_nra sm
        set sm.sm_status = '{1}'
        WHERE sm.sm_serialnum IN ('{0}')
        """.format(sim, status)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    return cur.rowcount


def set_imsi_status_bscs(con, imsi, status):
    cur = con.cursor()
    stmt = """
        update port@bscs_nra p
        set p.port_status = '{1}'
        WHERE p.port_num IN ('{0}')
            """.format(imsi, status)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    return cur.rowcount


if __name__ == "__main__":
    nra = nra_connection()
    print(get_sim_status(nra, '8948030322510315157'))
    nra.close()
