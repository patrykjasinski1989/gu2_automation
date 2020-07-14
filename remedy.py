"""This module is used for communicating with BMC Remedy ARS server."""
from datetime import datetime

from pyremedy import ARS, ARSError

import config

SERVER = config.REMEDY['server']
PORT = config.REMEDY['port']
ASSIGNEE = config.REMEDY['assignee']
USER = config.REMEDY['user']
PASSWORD = config.REMEDY['password']
SCHEMA_INC = 'HPD:Help Desk'
SCHEMA_WI = 'HPD:WorkLog'
SCHEMA_ATTACHMENTS = 'HPD:Attachments'


def get_incidents(group, tier1, tier2, tier3):
    """Return assigned incidents for given group and category."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        entries = ars.query(
            schema=SCHEMA_INC,
            qualifier=""" 'Status' = "Assigned"
                                 AND 'Assigned Group*+' = "%s" 
                                 AND 'Operational Categorization Tier 1' = "%s" 
                                 AND 'Operational Categorization Tier 2' = "%s" 
                                 AND 'Operational Categorization Tier 3' = "%s" 
                                 """ % (group, tier1, tier2, tier3),
            fields=['Incident Number', 'Detailed Decription', 'Description']
        )

        incidents = []
        for entry_id, entry_values in entries:
            notes = ''
            for field, value in entry_values.items():
                if field == 'Detailed Decription' and value:
                    notes = value.split('\n')
                elif field == 'Incident Number':
                    inc = value
                elif field == 'Description':
                    summary = value
            incidents.append({'id': entry_id, 'inc': inc, 'notes': notes, 'summary': summary})

        return incidents

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def get_all_incidents(group):
    """Return all assigned incidents for a given group (all categories)."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        entries = ars.query(
            schema=SCHEMA_INC,
            qualifier=""" 'Status' = "Assigned" 
                                 AND 'Assigned Group*+' = "%s"  
                                 AND ( 'Assignee' = NULL  
                                 OR 'Assignee' = "PATRYK JASIŃSKI"
                                 OR 'Assignee' = "JAN NALEŻYTY"
                                 )
                                 """ % group,
            fields=['Incident Number', 'Detailed Decription', 'Description', 'Assignee']
        )

        incidents = []
        for entry_id, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Detailed Decription':
                    if value:
                        notes = value.split('\n')
                    else:
                        notes = ''
                elif field == 'Incident Number':
                    inc = value
                elif field == 'Description':
                    summary = value
                elif field == 'Assignee':
                    assignee = value
            incidents.append({'id': entry_id, 'inc': inc, 'notes': notes, 'summary': summary, 'assignee': assignee})

        return incidents

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def close_incident(inc, resolution):
    """Resolve incident"""
    resolution = '\n'.join(list(set(resolution.split('\n'))))

    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        ars.update(
            schema=SCHEMA_INC,
            entry_id=inc['id'],
            entry_values={
                'Status': 'Resolved',
                'Status_Reason': 'Rozwiązane',
                'Assignee': ASSIGNEE,
                'Assignee Login ID': USER,
                'Resolution': resolution
            }
        )

        print('{} {}: {}'.format(str(datetime.now()).split('.')[0], inc['inc'], resolution.strip()))

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def hold_incident(inc, resolution):
    """This method is not used, because it does not work. Should be deleted."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        ars.update(
            schema=SCHEMA_INC,
            entry_id=inc['id'],
            entry_values={
                'Status': 'Pending',
                'Status_Reason': 'Requester Information',
                'Estimated Resolution Date': datetime(2018, 4, 14, 14, 4, 48),
                # (datetime.now() + timedelta((5-datetime.now().weekday()) % 7)).strftime("%Y-%m-%d %H:%M:%S"),
                'Assignee': ASSIGNEE,
                'Assignee Login ID': USER,
                'Resolution': resolution
            }
        )

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def assign_incident(inc):
    """Assign incident to me."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        ars.update(
            schema=SCHEMA_INC,
            entry_id=inc['id'],
            entry_values={
                'Status': 'Assigned',
                'Assignee': ASSIGNEE,
                'Assignee Login ID': USER
            }
        )

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def reassign_incident(inc, group):
    """Assign incident to another group."""
    if '_' not in group and 'Servicedesk' not in group:
        group_name = 'VC3_BSS_' + group.upper()
        if 'OM' in group.upper():
            group_name += '_PTK'
    else:
        group_name = group

    group_ids = {
        'VC3_BSS_OM_PTK': 'SGP000000051464',
        'VC3_BSS_NRA': 'SGP000000051463',
        'VC3_BSS_OV': 'SGP000000051269',
        'Servicedesk - KONTA': 'SGP000000040569',
        'APLIKACJE_OBRM_DOSTAWCA': 'SGP000000016581',
        'VC3_BSS_OV_TP': 'SGP000000051165',
        'VC3_BSS_CRM_FIX': 'SGP000000050968',
    }

    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        if group.upper() in ['OM_PTK', 'OV'] and group.upper not in ['OV_TP']:
            ars.update(
                schema=SCHEMA_INC,
                entry_id=inc['id'],
                entry_values={
                    'Categorization Tier 1': '000_incydent/awaria/uszkodzenie',
                    'Categorization Tier 2': 'OM',
                    'Categorization Tier 3': 'OM - TECHNIKA - INNE'
                }
            )
        elif group.upper() == 'NRA':
            ars.update(
                schema=SCHEMA_INC,
                entry_id=inc['id'],
                entry_values={
                    'Categorization Tier 1': '000_incydent/awaria/uszkodzenie',
                    'Categorization Tier 2': 'NRA',
                    'Categorization Tier 3': 'NRA - PROBLEM Z INNYMI DANYMI'
                }
            )

        if group_name == 'APLIKACJE_OBRM_DOSTAWCA':
            ars.update(
                schema=SCHEMA_INC,
                entry_id=inc['id'],
                entry_values={
                    'Assigned Group': group_name,
                    'Assigned Group ID': group_ids[group_name],
                    'Assigned Support Company': 'TELEKOMUNIKACJA POLSKA S.A.',
                    'Assigned Support Organization': 'Departament Rozwoju i Utrzymania Systemów IT',
                }
            )
        elif group_name == 'VC3_BSS_CRM_FIX':
            ars.update(
                schema=SCHEMA_INC,
                entry_id=inc['id'],
                entry_values={
                    'Assigned Group': group_name,
                    'Assigned Group ID': group_ids[group_name],
                    'Assigned Support Company': 'TELEKOMUNIKACJA POLSKA S.A.',
                    'Assigned Support Organization': 'IT (VENDOR)',
                }
            )
        else:
            ars.update(
                schema=SCHEMA_INC,
                entry_id=inc['id'],
                entry_values={
                    'Assigned Group': group_name,
                    'Assigned Group ID': group_ids[group_name]
                }
            )

        print('{} {} przekazany na grupę {}'.format(str(datetime.now()).split('.')[0], inc['inc'], group))

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def update_summary(inc, summary):
    """Update incident's summary."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        ars.update(
            schema=SCHEMA_INC,
            entry_id=inc['id'],
            entry_values={
                'Description': summary
            }
        )

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def get_work_info(inc):
    """Get work info contents for a given incident."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        entries = ars.query(
            schema=SCHEMA_WI,
            qualifier=""" 'Incident Number' = "%s" """ % inc['inc'],
            fields=['Description', 'Detailed Description', 'Submitter', 'Submit Date',
                    'Number of Attachments', 'z2AF Work Log01']
        )

        work_info = []
        for _, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Description':
                    summary = value
                elif field == 'Detailed Description':
                    notes = value.split('\n')
                elif field == 'Submitter':
                    submitter = value
                elif field == 'Submit Date':
                    submit_date = value
                elif field == 'Number of Attachments':
                    attachments_cnt = value
                elif field == 'z2AF Work Log01':
                    attachment = value
            work_info.append({'summary': summary, 'notes': notes, 'submitter': submitter, 'submit_date': submit_date,
                              'attachments_cnt': attachments_cnt, 'attachment': attachment})

        return work_info

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def add_work_info(inc, wi_summary, wi_notes):
    """Add work info to a given incident."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        ars.create(
            schema=SCHEMA_WI,
            entry_values={
                'Work Log Type': 'General Information',
                'Incident Number': inc['inc'],
                'Description': wi_summary,
                'Detailed Description': wi_notes
            }
        )

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
    finally:
        ars.terminate()


def get_fields(schema):
    """Get all fields for a given schema."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )
        fields = ars.fields(schema=schema)
        return fields
    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def get_schemas():
    """Get all schemas from Remedy database."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )
        schemas = ars.schemas()
        return schemas
    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def is_empty(inc):
    """Check if the incident is empty."""
    lines = inc['notes']
    if len(lines) > 4 \
            and '---[ dane identyfikacyjne komputera ]---' in lines[1] \
            and 'Lokalizacja: ' in lines[3] \
            and 'Telefony kontaktowe:' in lines[4]:
        return True
    return False


def has_attachment(work_info):
    """Check if there are any attachments."""
    for entry in work_info:
        if entry['attachments_cnt']:
            return True
    return False


def is_work_info_empty(work_info):
    """Check if there was any activity in work info."""
    return len(work_info) < 2


def has_exactly_one_entry(work_info):
    """Check if work info has exactly one human-generated entry."""
    if not work_info or len(work_info) < 2:
        return False
    return len([entry for entry in work_info if 'Work' not in entry['summary']]) == 1


def get_pending_incidents(groups):
    """Return pending incidents related to a problem for a given list of groups."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        qualifier = """'Status' = "Pending" AND 'Status_Reason_Hidden' = "Problem" AND ("""
        for group in groups:
            qualifier += """'Assigned Group*+' = "%s" OR """ % group
        qualifier = qualifier[:-3]
        qualifier += ")"

        entries = ars.query(
            schema=SCHEMA_INC,
            qualifier=qualifier,
            fields=['Incident Number', 'Problem ID', 'Detailed Decription', 'Reported Date']
        )

        incidents = []
        for entry_id, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Incident Number':
                    inc = value
                elif field == 'Problem ID':
                    pbi = value
                elif field == 'Detailed Decription':
                    notes = value.split('\r\n')
                elif field == 'Reported Date':
                    reported_date = value
            incidents.append({'id': entry_id, 'inc': inc, 'pbi': pbi, 'notes': notes, 'reported_date': reported_date})

        return incidents

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()


def get_resolved_incidents(groups):
    """Return resolved incidents for a given list of groups."""
    try:
        ars = ARS(
            server=SERVER, port=PORT,
            user=USER, password=PASSWORD
        )

        qualifier = """'Status' = "Resolved" AND ("""
        for group in groups:
            qualifier += """ '1000000217' = "%s" OR """ % group
        qualifier = qualifier[:-3]
        qualifier += ")"

        entries = ars.query(
            schema=SCHEMA_INC,
            qualifier=qualifier,
            fields=['Assigned Group', 'Assignee']
        )

        incidents = []
        for _, entry_values in entries:
            for field, value in entry_values.items():
                if field == 'Assigned Group':
                    assigned_group = value
                elif field == 'Assignee':
                    assignee = value
            incidents.append({'assigned_group': assigned_group, 'assignee': assignee})

        return incidents

    except ARSError as ars_ex:
        print('ERROR: {}'.format(ars_ex))
        return ars_ex
    finally:
        ars.terminate()
