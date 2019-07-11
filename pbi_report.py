import operator

from remedy import get_pending_incidents

if __name__ == "__main__":

    groups = ['CDT', 'CV', 'ML', 'OPTIPOS_FIX', 'OPTIPOS_MOBILE', 'RSW', 'SIS']
    groups = ['VC3_BSS_' + g for g in groups]

    pbi_counter = {}
    incidents = get_pending_incidents(groups)
    incidents = [i for i in incidents if i['pbi'] is not None]
    for inc in incidents:
        pbi = inc['pbi']
        if pbi in pbi_counter:
            pbi_counter[pbi] += 1
        else:
            pbi_counter[pbi] = 1

    for pbi, count in sorted(pbi_counter.items(), key=operator.itemgetter(1), reverse=True):
        print(pbi, count)
    print('-' * 80)
    print('total:', len(incidents))
