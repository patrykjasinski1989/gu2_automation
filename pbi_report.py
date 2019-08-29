"""This scripts returns a list of PBIs sorted by amount of related incidents."""
import operator

from remedy import get_pending_incidents

if __name__ == "__main__":

    GROUPS = ['CDT', 'CV', 'ML', 'OPTIPOS_FIX', 'OPTIPOS_MOBILE', 'RSW', 'SIS']
    GROUPS = ['VC3_BSS_' + g for g in GROUPS]

    PBI_COUNTER = {}
    INCIDENTS = get_pending_incidents(GROUPS)
    INCIDENTS = [i for i in INCIDENTS if i['pbi'] is not None]
    for inc in INCIDENTS:
        pbi = inc['pbi']
        if pbi in PBI_COUNTER:
            PBI_COUNTER[pbi] += 1
        else:
            PBI_COUNTER[pbi] = 1

    for pbi, count in sorted(PBI_COUNTER.items(), key=operator.itemgetter(1), reverse=True):
        print(pbi, count)
    print('-' * 80)
    print('total:', len(INCIDENTS))
