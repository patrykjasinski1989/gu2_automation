import operator

from remedy import get_pending_incidents

if __name__ == "__main__":

    groups = ['VC_BSS_MOBILE_OPTIPOS', 'VC_BSS_MOBILE_RSW', 'VC_BSS_MOBILE_CDT', 'VC_BSS_MOBILE_SIS',
              'VC_BSS_MOBILE_BK-MERITUM', 'VC_BSS_MOBILE_ML', 'VC_BSS_MOBILE_CV', 'VC_BSS_MOBILE_BLV',
              'VC_BSS_MOBILE_BLACKCHECK']

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
        if count > 5:
            print(pbi, count)
    print('-' * 80)
    print('total:', len(incidents))
