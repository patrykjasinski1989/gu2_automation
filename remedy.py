# -*- coding: utf-8 -*-
from pyremedy import ARS, ARSError

import config

server = config.remedy['server']
port = config.remedy['port']
user = config.remedy['user']
password = config.remedy['password']


def get_incidents(group, tier1, tier2, tier3):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        entries = ars.query(
            schema='HPD:Help Desk Classic',
            qualifier="""'Status*' = "Assigned"
                                 AND 'Assigned Group*+' = "%s"
                                 AND 'Operational Categorization Tier 1' = "%s"
                                 AND 'Operational Categorization Tier 2' = "%s"
                                 AND 'Operational Categorization Tier 3' = "%s"
                                 """ % (group, tier1, tier2, tier3),
            fields=['Incident Number', 'Detailed Decription', 'Description']
        )

        incidents = []
        for entry_id, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Detailed Decription':
                    notes = value.split('\n')
                elif field == 'Incident Number':
                    inc = value
                elif field == 'Description':
                    summary = value
            incidents.append({'id': entry_id, 'inc': inc, 'notes': notes, 'summary': summary})

        return incidents

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def close_incident(inc, resolution):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        ars.update(
            schema='HPD:Help Desk Classic',
            entry_id=inc['id'],
            entry_values={
                'Status': 'Resolved',
                'Status_Reason': 'Rozwiązane',
                'Assignee': 'PATRYK JASIŃSKI',
                'Assignee Login ID': 'jasinpa4',
                'Resolution': resolution
            }
        )

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def reassign_incident(inc, group):

    if '_' not in group and 'Servicedesk' not in group:
        group_name = 'VC_BSS_MOBILE_' + group.upper()
    else:
        group_name = group

    group_ids = {'VC_BSS_MOBILE_OM': 'SGP000000024567',
                 'VC_BSS_MOBILE_NRA': 'SGP000000024570',
                 'VC_BSS_MOBILE_OV': 'SGP000000024585',
                 'Servicedesk - KONTA': 'SGP000000040569'}

    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        ars.update(
            schema='HPD:Help Desk Classic',
            entry_id=inc['id'],
            entry_values={
                'Assigned Group': group_name,
                'Assigned Group ID': group_ids[group_name]
            }
        )

        if group.upper() in ['OM', 'OV']:
            ars.update(
                schema='HPD:Help Desk Classic',
                entry_id=inc['id'],
                entry_values={
                    'Categorization Tier 2': 'OM',
                    'Categorization Tier 3': 'OM - TECHNIKA - INNE'
                }
            )

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def update_summary(inc, summary):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        ars.update(
            schema='HPD:Help Desk Classic',
            entry_id=inc['id'],
            entry_values={
                'Description': summary
            }
        )

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def get_work_info(inc):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        entries = ars.query(
            schema='HPD:WorkLog',
            qualifier=""" 'Incident Number' = "%s" """ % inc,
            fields=['Description', 'Detailed Description', 'Submitter', 'Submit Date']
        )

        incidents = []
        for entry_id, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Description':
                    summary = value
                elif field == 'Detailed Description':
                    notes = value.split('\n')
                elif field == 'Submitter':
                    submitter = value
                elif field == 'Submit Date':
                    submit_date = value
            incidents.append({'summary': summary, 'notes': notes, 'submitter': submitter, 'submit_date': submit_date})

        return incidents

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def add_work_info(inc, summary, notes):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        ars.create(
            schema='HPD:WorkLog',
            entry_values={
                'Work Log Type': 'General Information',
                'Incident Number': inc,
                'Description': summary,
                'Detailed Description': notes
            }
        )

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def get_fields(schema):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )
        fields = ars.fields(schema=schema)
        return fields
    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def get_schemas():
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )
        schemas = ars.schemas()
        return schemas
    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def is_empty(inc):
    lines = inc['notes']
    if '---[ dane identyfikacyjne komputera ]---' in lines[1] \
            and 'Lokalizacja: ' in lines[3] \
            and 'Telefony kontaktowe:' in lines[4]:
                return True
    else:
        return False
