# -*- coding: utf-8 -*-
from pyremedy import ARS, ARSError
import config

server = config.remedy['server']
port = config.remedy['port']
user = config.remedy['user']
password = config.remedy['password']


def getIncidents(group, tier1, tier2, tier3):
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
            fields=['Incident Number', 'Detailed Decription', 'Description' ]
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


def closeIncident(inc, resolution):
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


def reassignIncident(inc, group):

    if '_' not in group:
        group_name = 'VC_BSS_MOBILE_' + group.upper()

    group_ids = {'VC_BSS_MOBILE_OM': 'SGP000000024567',
                 'VC_BSS_MOBILE_NRA': 'SGP000000024570'}

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

        if group.upper() == 'OM':
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


def updateSummary(inc, summary):
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


def addWorkInfo(inc, summary, notes):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )
        # TODO

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()


def getFields(schema):
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


def getSchemas():
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


def emptyInc(inc):
    lines = inc['notes']
    if '---[ dane identyfikacyjne komputera ]---' in lines[1] \
            and 'Lokalizacja: ' in lines[3] \
            and 'Telefony kontaktowe:' in lines[4]:
                return True
    else:
        return False


"""
def updateWorkInfo(id, summary, notes):
    try:
        ars = ARS(
            server=server, port=port,
            user=user, password=password
        )

        ars.update(
            schema='HPD:Help Desk Classic',
            entry_id=id,
            entry_values={

            }
        )

    except ARSError as e:
        print('ERROR: {}'.format(e))
        return e
    finally:
        ars.terminate()
"""
