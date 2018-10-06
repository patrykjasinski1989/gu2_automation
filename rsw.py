# -*- coding: utf-8 -*-
import cx_Oracle

import config


def rsw_connection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.rsw['user'], config.rsw['password'], config.rsw['server']))


def get_order_id(con, msisdn, status):
    cur = con.cursor()
    cur.execute('select max(id_zamowienia) from rsw.rsw_zamowienia '
                'where dn_num = \'' + str(msisdn) + '\' and status = ' + str(status))
    row = cur.fetchone()
    cur.close()
    return row[0]


def set_order_status(con, order_id, status):
    cur = con.cursor()
    cur.execute('update rsw.rsw_zamowienia set status = ' + str(status) + ' where id_zamowienia = ' + str(order_id))
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def get_latest_order(con, msisdn):
    cur = con.cursor()
    cur.execute('select * from (select id_zamowienia, data_zamowienia, status, status_om, ilosc_prob '
                "from rsw.rsw_zamowienia where dn_num = '{}') where rownum = 1".format(msisdn))
    row = cur.fetchone()
    cur.close()
    if cur.rowcount == 1:
        dict_row = {'id_zamowienia': row[0], 'data_zamowienia': row[1],
                    'status': row[2], 'status_om': row[3], 'ilosc_prob': row[4]}
    else:
        dict_row = None
    return dict_row


def add_entitlement(con, msisdn, offer_id=6021):
    cur = con.cursor()
    cur.execute("""
    declare
        v_msisdn rsw.rsw_zamowienia.dn_num%type := '{}';
        v_id_oferty rsw.rsw_uprawnienia.id_oferty%type := '{}';
        v_co_id rsw.rsw_zamowienia.co_id%type;
        v_ins_prod_id rsw.rsw_zamowienia.ins_prod_id%type;
    begin
        select max(co_id) into v_co_id from rsw.rsw_zamowienia where dn_num = v_msisdn;
        select max(ins_prod_id) into v_ins_prod_id from rsw.rsw_zamowienia where dn_num = v_msisdn;
        insert into rsw.rsw_uprawnienia (co_id, co_expir_date, data_upawnienia, data_waznosci, user_id, id_oferty, staz, ins_prod_id, msisdn, ignorowanie_warunkow_oferty)
        values (v_co_id, trunc(sysdate), trunc(sysdate), trunc(sysdate+365), 'matprotas', v_id_oferty, 52, v_ins_prod_id, v_msisdn, 1);
        commit;
    end;
    """.format(msisdn, offer_id))
    cur.close()
    return 0
