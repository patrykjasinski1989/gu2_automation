"""This module contains logic for releasing reserved SIM cards."""
from db.nra import nra_connection, get_sim_status, set_sim_status_nra, set_sim_status_bscs, set_imsi_status_bscs
from db.otsa import check_sim
from remedy import add_work_info, reassign_incident


def process_sims(sims, otsa, inc):
    """This function changes SIM card statuses, if allowed and necessary.
    If the status is 'd', 'l', or 'E', then we change it to 'r' and close the ticket.
    If it's 'a' or 'B' or there is an open transaction with this card, we don't change the status.
    All other cases (less than 1%) must be handled manually."""
    all_resolved = True
    resolution = ''

    nra = nra_connection()
    for sim in sims:
        partial_resolution = ''
        result = check_sim(otsa, sim)
        result = [r for r in result if r['status'] not in ('3D', '3G')]
        if not result:
            wi_notes = ''
            sim_status = get_sim_status(nra, sim)
            if not sim_status:
                partial_resolution = 'Brak karty SIM {0} w nRA. Proszę podać poprawny numer.'.format(sim)
                resolution = partial_resolution + '\r\n'
                continue
            if sim_status['status_nra'] == sim_status['status_bscs']:
                if sim_status['status_nra'] in ('r', 'd', 'l', 'E') \
                        and sim_status['status_nra'] == sim_status['status_bscs']:
                    set_sim_status_nra(nra, sim, 'r')
                    set_sim_status_bscs(nra, sim, 'r')
                    set_imsi_status_bscs(nra, sim_status['imsi'], 'r')
                    partial_resolution = 'Karta SIM {0} uwolniona.'.format(sim)
                elif sim_status['status_nra'] in ('a', 'B'):
                    partial_resolution = 'Karta SIM {0} aktywna. Brak możliwości odblokowania.'.format(sim)
                else:
                    all_resolved = False
                    wi_notes += 'Karta SIM {} w statusie {}.\nW Optiposie brak powiązań.'.format(sim, sim_status)
            if wi_notes:
                add_work_info(inc, 'VC_OPTIPOS', wi_notes)
                reassign_incident(inc, 'NRA')
        else:
            partial_resolution = 'Karta SIM {0} powiązana z nieanulowaną umową {1}. ' \
                                 'Brak możliwości odblokowania. ' \
                                 'Proszę o kontakt z dealer support lub z działem reklamacji.' \
                .format(sim, result[0]['trans_num'])
        if partial_resolution != '':
            resolution = resolution + '\r\n' + partial_resolution
    nra.close()

    return all_resolved, resolution
