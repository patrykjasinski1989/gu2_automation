from time import sleep

import paramiko

import config
from om_tp import get_order_info, get_order_data


def resubmit_orders():
    tel_order_numbers = """

    """.split()

    user = config.OM_TP['user']
    password = config.OM_TP['password']
    ssh_client = paramiko.SSHClient()

    for i, tel_order_number in enumerate(tel_order_numbers):
        order_data = get_order_data(get_order_info(tel_order_number))
        resubmit_order_link = 'https://126.185.9.192:5555/invoke/tp.ordermanagement.console.pub/resubmitOrder?ordId='
        if 'OM zamowienie (ORD_ID)' in order_data:
            resubmit_order_link += order_data['OM zamowienie (ORD_ID)']
        else:
            continue

        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(config.EAI_IS['server'], username=config.EAI_IS['user'], password=config.EAI_IS['password'],
                           allow_agent=False)
        _, stdout, _ = ssh_client.exec_command('curl -k -u {}:{} {}'.format(user, password, resubmit_order_link))
        print(i, resubmit_order_link)
        sleep(5)

    ssh_client.close()


if __name__ == '__main__':
    resubmit_orders()
