# -*- coding: utf-8 -*-
import cx_Oracle

import config


def ml_sti_connection():
    dsn_tns = cx_Oracle.makedsn(config.ml_sti['ip'], config.ml_sti['port'], config.ml_sti['sid'])
    return cx_Oracle.connect(user=config.ml_sti['user'], password=config.ml_sti['password'], dsn=dsn_tns)


def delete_account(con, login, inc):
    cur = con.cursor()
    stmt = """ UPDATE ml.bezp_kontroladostepu SET
                enabled = 'F',
                uwagi = '{} likwidacja konta'
                WHERE LOWER(login) = LOWER('{}') """.format(inc['inc'], login)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def create_account(con, login, date, profile, inc):
    cur = con.cursor()
    stmt = """ INSERT INTO ml.bezp_kontroladostepu (
                login, expiration_date, enabled, profile, uwagi, id, bscs_dealer_id, bscs_dealer_code, bscs_code )
                SELECT '{login}', to_date('{date}', 'YYYY-MM-DD HH24:MI:SS'), 'T', '{profile}', '{inc} zalozenie konta',
                (SELECT MAX(id) + 1 FROM ml.bezp_kontroladostepu), -45800, 'KTML1', 'KTML1'
                FROM DUAL
                WHERE NOT EXISTS (SELECT 1 FROM ml.bezp_kontroladostepu WHERE enabled = 'T' 
                AND LOWER(login) = LOWER('{login}')) """.format(login=login, date=date, profile=profile, inc=inc)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


def recertify_account(con, login, date, profile, inc):
    cur = con.cursor()
    stmt = """ UPDATE ml.bezp_kontroladostepu SET
                enabled = 'T',
                uwagi = '{inc} recertyfikacja',
                expiration_date = to_date('{date}', 'YYYY-MM-DD HH24:MI:SS'),
                profile = '{profile}'
                WHERE LOWER(login) = LOWER('{login}') """.format(login=login, date=date, profile=profile, inc=inc)
    cur.execute(stmt)
    if cur.rowcount == 1:
        con.commit()
    else:
        con.rollback()
    cur.close()
    return cur.rowcount


if __name__ == '__main__':
    ml_sti = ml_sti_connection()
    print(ml_sti)
    ml_sti.close()
