"""This module is used for getting data from RSW database."""
import config
from db.db_helpers import execute_dml, connect


def rsw_connection():
    """Return a connection to RSW database."""
    return connect('RSW-DB', config.RSW)


def get_order_id(con, msisdn, status):
    """Return last order for a given msisdn and status."""
    cur = con.cursor()
    cur.execute('select max(id_zamowienia) from rsw.rsw_zamowienia '
                'where dn_num = \'' + str(msisdn) + '\' and status = ' + str(status))
    row = cur.fetchone()
    cur.close()
    return row[0]


def set_order_status(con, order_id, status):
    """Set order status for a given order_id."""
    stmt = 'update rsw.rsw_zamowienia set status = ' + str(status) + ' where id_zamowienia = ' + str(order_id)
    return execute_dml(con, stmt)


def get_latest_order(con, msisdn):
    """Return last order for a given MSISDN number."""
    cur = con.cursor()
    cur.execute("select * from (select id_zamowienia, data_zamowienia, status, status_om, ilosc_prob "
                "from rsw.rsw_zamowienia where dn_num = '{}' order by data_zamowienia desc) where rownum = 1"
                .format(msisdn))
    row = cur.fetchone()
    cur.close()
    if cur.rowcount == 1:
        dict_row = {'id_zamowienia': row[0], 'data_zamowienia': row[1],
                    'status': row[2], 'status_om': row[3], 'ilosc_prob': row[4]}
    else:
        dict_row = None
    return dict_row


def make_offer_available(con, msisdn, offer_id_=6021):
    """Execute a procedure to make an offer available for a given MSISDN number."""
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
    """.format(msisdn, offer_id_))
    cur.close()
    return 0


def get_offer_id_by_name(con, offer_name):
    """Find offer id by name."""
    if not offer_name:
        return None
    offer_name = ''.join([c if ord(c) < 128 else '_' for c in offer_name])
    cur = con.cursor()
    stmt = """select id_oferty from rsw.rsw_oferty where lower(nazwa_oferty) like lower('%{}%')""".format(offer_name)
    cur.execute(stmt)
    offer_id_ = cur.fetchone()
    cur.close()
    if offer_id_:
        return offer_id_[0]
    return None


if __name__ == '__main__':
    RSW = rsw_connection()
    OFFER_ID = get_offer_id_by_name(RSW, 'prepaid')
    print(OFFER_ID)
