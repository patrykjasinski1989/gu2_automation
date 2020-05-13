#!/usr/bin/env python3
"""This script generates statistics about incidents resolved by everyone in the last two weeks."""
import argparse
from remedy import get_resolved_incidents

TOTAL = 'TOTAL'
GROUPS_VAS = ['CCGW', 'EPGW', 'EXTRANET', 'FM', 'IPK', 'KSRZ', 'LBS', 'LBS_PLI_CBD', 'MOBLGW', 'NOTYFIKATOR_PTK',
              'NOTYFIKATOR_TP', 'QUICKDOC', 'RPK', 'SMSEX', 'UCPGW', 'UCPSMS']
GROUPS_CRM = ['CRM_MOBILE', 'ICC', 'MVNE', 'ISCO', 'ALLEINFO', 'CBS', 'MOPUP', 'OSIW', 'SOKX', 'CRM_FIX', 'REDA',
              'TIGER']
GROUPS_INT = ['BDAA', 'EAI_PTK', 'IMEIBL', 'JAZZ', 'NRA', 'OM_PTK', 'OV', 'PREAKTYWATOR', 'ODS', 'OM_TP', 'OV_TP',
              'EAI_TP']
GROUPS_SALES = ['CV', 'CDT', 'ML', 'OPTIPOS_MOBILE', 'RSW', 'SIS', 'OPTIPOS_FIX', 'WMM']
GROUPS_OF = ['BAM', 'OREDR_FLOW']
GROUPS_ALL = GROUPS_VAS + GROUPS_CRM + GROUPS_INT + GROUPS_SALES + GROUPS_OF


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
    parser = argparse.ArgumentParser(description='Show resolution stats for the chosen team.')
    parser.add_argument('-t', '--team', required=True, choices=('vas', 'crm', 'int', 'sales', 'of', 'all'))
    team_name = parser.parse_args().team
    group_list_name = 'GROUPS_' + team_name.upper()
    groups = globals()[group_list_name]

    remedy_groups = ['VC3_BSS_' + g for g in groups]
    resolved_incidents = get_resolved_incidents(remedy_groups)

    stats, group_stats = {}, {}
    for group in groups:
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
