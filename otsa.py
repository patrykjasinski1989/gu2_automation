# -*- coding: utf-8 -*-
import cx_Oracle

import config


def otsa_connection():
    return cx_Oracle.connect('{}/{}@{}'.format(config.otsa['user'], config.otsa['password'], config.otsa['server']))


def search_msisdn(con, msisdn):
    cur = con.cursor()
    cur.execute('select t.cart_code, t.trans_code, con.msisdn, t.status, t.ncs_trans_num, t.om_order_id, '
                't.process_error, t.ncs_error_desc, t.trans_type, t.author_user_code, t.trans_num, t.create_date, '
                'crm_customer_id, t.custcode from ptk_otsa_transaction t, ptk_otsa_trans_contract con '
                'where t.trans_code = con.trans_code (+) and con.msisdn = \'' + str(msisdn) + '\'')
    rows = cur.fetchall()
    if len(rows) == 0:
        cur.execute('select t.cart_code, t.trans_code, t.msisdn, t.status, t.ncs_trans_num, t.om_order_id, '
                    't.process_error, t.ncs_error_desc, t.trans_type, t.author_user_code, t.trans_num, t.create_date, '
                    'crm_customer_id, t.custcode from ptk_otsa_transaction t where t.msisdn = \'' + str(msisdn) + '\'')
        rows = cur.fetchall()
    cur.close()
    dict_rows = []
    for row in rows:
        dict_rows.append({'cart_code': row[0], 'trans_code': row[1], 'msisdn': row[2], 'status': row[3],
                          'ncs_trans_num': row[4], 'om_order_id': row[5], 'process_error': row[6],
                          'ncs_error_desc': row[7], 'trans_type': row[8], 'author_user_code': row[9],
                          'trans_num': row[10], 'create_date': row[11], 'crm_customer_id': row[12],
                          'custcode': row[13]})
    return dict_rows


def search_cart(con, cart_code):
    cur = con.cursor()
    try:
        cur.execute('select t.cart_code, t.trans_code, t.status, t.ncs_trans_num, t.om_order_id, '
                    't.process_error, t.ncs_error_desc, t.trans_type, t.author_user_code, t.trans_num, t.create_date, '
                    'crm_customer_id, t.custcode from ptk_otsa_transaction t where t.cart_code = \'' +
                    str(cart_code) + '\'')
        rows = cur.fetchall()
    except:
        cur.close()
        return []
    cur.close()
    dict_rows = []
    for row in rows:
        dict_rows.append({'cart_code': row[0], 'trans_code': row[1], 'status': row[2],
                          'ncs_trans_num': row[3], 'om_order_id': row[4], 'process_error': row[5],
                          'ncs_error_desc': row[6], 'trans_type': row[7], 'author_user_code': row[8],
                          'trans_num': row[9], 'create_date': row[10], 'crm_customer_id': row[11],
                          'custcode': row[12]})
    return dict_rows


def update_transaction(con, trans_code, status):
    cur = con.cursor()
    cur.execute('update ptk_otsa_transaction set status = \'' + str(status) + '\' '
                                                                              'where trans_code = \'' + str(
        trans_code) + '\'')
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def update_contract(con, trans_code, status):
    cur = con.cursor()
    cur.execute('update ptk_otsa_trans_contract set status = \'' + str(status) + '\' '
                                                                                 'where trans_code = \'' + str(
        trans_code) + '\'')
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def fix_90100(con, trans_code):
    cur = con.cursor()
    cur.execute('update ptk_otsa_trans_address set country = 18 where trans_code = \'' + str(trans_code) + '\'')
    if cur.rowcount == 3:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def fix_csc185(con, cart_code):
    cur = con.cursor()
    cur.execute('update ptk_otsa_transaction set fname = upper(fname), pers_fname = upper(pers_fname), '
                'lname = upper(lname), pers_lname = upper(pers_lname) '
                'where cart_code = \'' + str(cart_code) + '\'')
    con.commit()
    cur.close()
    return cur.rowcount


def fix_csc178(con, cart_code):
    return fix_csc185(con, cart_code)


def fix_csc598(con, trans_code):
    cur = con.cursor()
    cur.execute('insert into ptk_otsa_trans_address_type '
                'select distinct address_code, 1 from ptk_otsa_trans_address '
                'where trans_code = \'' + str(trans_code) + '\'')
    con.commit()
    cur.close()
    return cur.rowcount


def fix_pesel(con, trans_code):
    cur = con.cursor()
    cur.execute('update ptk_otsa_transaction set comptaxno = \'\', pers_comptaxno = \'\''
                'where trans_code = \'' + str(trans_code) + '\'')
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def fix_aac(con, trans_code, bscs_customer_id):
    cur = con.cursor()
    cur.execute("update ptk_otsa_transaction set bscs_customer_id = '" + str(bscs_customer_id) +
                "', new_customer = 'N' where trans_code = '" + str(trans_code) + "'")
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def check_sim(con, sim):
    cur = con.cursor()
    cur.execute('select t.imei, tr.cart_code, t.trans_code, \'contract\', tr.create_date, tr.status, tr.trans_num '
                'from ptk_otsa_transaction tr, ptk_otsa_trans_contract t where sm_serialnum = \'' + str(sim) + '\' '
                'and t.trans_code=tr.trans_code union '
                'select t.res, tr.cart_code, t.trans_code, \'reserved\', tr.create_date, tr.status, tr.trans_num '
                'from ptk_otsa_transaction tr, ptk_otsa_trans_reserved_res t where t.res = \'' + str(sim) + '\' '
                'and t.trans_code=tr.trans_code')
    rows = cur.fetchall()
    cur.close()
    dict_rows = []
    for row in rows:
        dict_rows.append({'sim': row[0], 'cart_code': row[1], 'trans_code': row[2], 'type': row[3],
                          'create_date': row[4], 'status': row[5], 'trans_num': row[6]})
    return dict_rows


def update_cart(con, trans_code, cart_code):
    cur = con.cursor()
    cur.execute('update ptk_otsa_transaction set cart_code = \'' + cart_code +
                '\' where trans_code = \'' + trans_code + '\'')
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def unlock_account(con, login):
    cur = con.cursor()
    cur.execute('UPDATE ptk_otsa_user u SET u.password =  \'xhjt1p6C4H\', u.status = \'A\', '
                'u.Last_Password_Change= sysdate, u.key_active =\'Y\', u.prev_failed_logins = u.failed_logins, '
                'u.failed_logins = 0, u.last_login = sysdate Where U.Login = \'' + login + '\'')
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount
