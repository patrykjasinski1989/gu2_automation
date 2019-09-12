"""This module stores all connection strings to production databases but without logins and passwords.
Used to be uploaded to the repository instead of config.py"""

REMEDY = {'server': '126.185.108.140',
          'port': 60000,
          'assignee': '',
          'user': '',
          'password': ''}

# sales config

OTSA = {'server': '10.236.28.107:1521/OTSA',
        'user': '',
        'password': ''}

RSW = {'server': '10.236.28.53:1521/RSW',
       'user': '',
       'password': ''}

NRA = {'server': '10.236.28.66:1526/NRA',
       'user': '',
       'password': ''}

BSCS = {'server': '10.236.28.81:1526/BSCS',
        'user': '',
        'password': ''}

OPTIPOS = {'server': '10.236.28.114:1551/OPTIPOS',
           'user': '',
           'password': ''}

ML_STI = {'server': '10.12.116.25:1521/NIRSW2',
          'user': '',
          'password': ''}

ML_PROD = ML = RSW

EAI = {'server': 'http://10.236.14.11:4125'}

OM_PTK = {'server': 'http://172.30.70.10:6655',
          'user': '',
          'password': ''}

OPTPOS_LOGS = {'server': '172.30.48.187',
               'user': '',
               'password': ''}

# int config

OM_TP = {'server': 'https://126.185.9.192:5555',
         'user': '',
         'password': ''}

EAI_IS = {'server': '',
          'user': '',
          'password': ''}
