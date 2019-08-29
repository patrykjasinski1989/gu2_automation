"""This module stores all connection strings to production databases but without logins and passwords.
Used to be uploaded to the repository instead of config.py"""

REMEDY = {'server': '126.185.108.140',
          'port': 60000,
          'user': '',
          'password': ''}

OM_PTK = {'server': 'http://172.30.70.10:6655',
          'user': '',
          'password': ''}

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

EAI = {'server': 'http://10.236.14.11:4125'}

ML = RSW

ML_PROD = ML

ML_STI = {'user': '',
          'password': '',
          'ip': '10.12.116.25',
          'port': 1521,
          'sid': 'NIRSW2'}

OPTPOS_LOGS = {'server': '172.30.48.187',
               'user': '',
               'password': ''}
