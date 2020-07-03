import paramiko

import config
from om_tp import get_order_info, get_order_data


def resubmit_orders():
    tel_order_numbers = """
    TEL000128823868
    TEL000128835948
    TEL000128752983
    TEL000128761262
    TEL000128734059
    TEL000128772114
    TEL000128840657
    """.split()

    user = config.OM_TP['user']
    password = config.OM_TP['password']
    ssh_client = paramiko.SSHClient()

    for tel_order_number in tel_order_numbers:
        order_data = get_order_data(get_order_info(tel_order_number))
        resubmit_order_link = 'https://126.185.9.192:5555/invoke/tp.ordermanagement.console.pub/resubmitOrder?ordId='
        resubmit_order_link += order_data['OM zamowienie (ORD_ID)']

        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(config.EAI_IS['server'], username=config.EAI_IS['user'], password=config.EAI_IS['password'],
                           allow_agent=False)
        _, stdout, _ = ssh_client.exec_command('curl -k -u {}:{} {}'.format(user, password, resubmit_order_link))
        print(resubmit_order_link)

    ssh_client.close()


if __name__ == '__main__':
    resubmit_orders()
