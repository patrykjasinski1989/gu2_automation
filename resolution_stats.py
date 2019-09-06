#!/usr/bin/env python3
"""This script generates statistics about incidents resolved by everyone in the last two weeks."""
from remedy import get_resolved_incidents

TOTAL = 'TOTAL'
GROUPS = ['CDT', 'CV', 'ML', 'OPTIPOS_FIX', 'OPTIPOS_MOBILE', 'RSW', 'SIS']

GROUPS = ['CRM_MOBILE', 'ICC', 'MVNE', 'ISCO', 'ALLEINFO', 'CBS', 'CRM_FIX', 'MOPUP', 'OSIW', 'SOKX', 'REDA', 'TIGER',
          'BDAA', 'EAI_PTK', 'IMEIBL', 'JAZZ', 'NRA', 'OM_PTK', 'OV', 'PREAKTYWATOR', 'ODS', 'OM_TP', 'OV_TP', 'EAI_TP',
          'WMM', 'CV', 'CDT', 'ML', 'OPTIPOS_MOBILE', 'RSW', 'SIS', 'OPTIPOS_FIX', 'CCGW', 'EPGW', 'EXTRANET', 'FM',
          'IPK', 'KSRZ', 'LBS', 'LBS_PLI_CBD', 'MOBLGW', 'NOTYFIKATOR_PTK', 'NOTYFIKATOR_TP', 'QUICKDOC', 'RPK',
          'SMSEX', 'UCPGW', 'UCPSMS', 'BAM']


def aggregate_stats(stats, aggr1, aggr2):
    """Aggregate stats :) Works similar to collections.Counter, just has two levels of aggregation."""
    if aggr1 not in stats:
        stats[aggr1] = {}
        stats[aggr1][TOTAL] = 1
    else:
        stats[aggr1][TOTAL] += 1

    if aggr2 not in stats[aggr1]:
        stats[aggr1][aggr2] = 1
    else:
        stats[aggr1][aggr2] += 1

    return stats


def print_stats(stats, details=False):
    """Print aggregated stats, with details or not."""
    key1_order = sorted(stats, key=lambda x: -stats[x][TOTAL])
    for key1 in key1_order:
        print('{} {}'.format(key1, stats[key1][TOTAL]))
        if details:
            key2_order = sorted(stats[key1], key=lambda x: -stats[key1][x])
            for key2 in key2_order:
                if key2 != TOTAL:
                    print('\t{} {}'.format(key2, stats[key1][key2]))
            print('')


def main():
    """Generate and print stats."""
    remedy_groups = ['VC3_BSS_' + g for g in GROUPS]
    resolved_incidents = get_resolved_incidents(remedy_groups)

    stats, group_stats = {}, {}
    for group in GROUPS:
        group_stats[group] = {TOTAL: 0}

    for inc in resolved_incidents:
        assignee = inc['assignee']
        assigned_group = inc['assigned_group'].replace('VC3_BSS_', '')
        stats = aggregate_stats(stats, assignee, assigned_group)
        group_stats = aggregate_stats(group_stats, assigned_group, assignee)

    print_stats(stats, details=True)
    print('*' * 80)
    print_stats(group_stats, details=True)


if __name__ == '__main__':
    main()
