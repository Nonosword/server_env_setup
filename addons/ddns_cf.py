# /root/DDNS/ddns_cf.py
import os
import requests
import subprocess
import re
from dotenv import load_dotenv
load_dotenv()


def update_dns_record(zone_id, api_key, current_ipv4, current_ipv6):
    dns_records_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    response = requests.get(dns_records_url, headers=headers)
    response_data = response.json()

    if response.status_code == 200:
        dns_records = response_data['result']
        if dns_records:
            items = len(dns_records)
            for i in range(items):
                dns_records_id = dns_records[i]['id']
                prev_ip = dns_records[i]['content']
                dns_name = dns_records[i]['name']
                dns_type = dns_records[i]['type']
                if dns_type == 'A':
                    current_ip = current_ipv4
                elif dns_type == 'AAAA':
                    current_ip = current_ipv6
                else:
                    print(f'DNS record type not supported: {dns_type}.')
                    continue

                if current_ip != prev_ip:
                    update_url = f'{dns_records_url}/{dns_records_id}'
                    payload = {
                        "content": current_ip,
                        "name": dns_name,
                        "type": dns_type,
                    }
                    update_response = requests.patch(update_url, json=payload, headers=headers)

                    if update_response.status_code == 200:
                        print('DNS record updated successfully.')
                        print(f'{dns_name} {dns_type} record update: {prev_ip} -> {current_ip}')
                    else:
                        print(f'Failed to update DNS record for {dns_name}.')
                else:
                    print(f'IP has not changed. No update needed for {dns_name}.')
        else:
            print('DNS record not found.')
    else:
        print('Failed to retrieve DNS records.')


def get_interface_ipv6():
    interfaces = ['eth0', 'wg0', 'ens5', 'enp1s0']
    for interface in interfaces:
        try:
            addr_output = subprocess.check_output(['ip', '-6', 'addr', 'show', interface], text=True)
            match = re.search(r'inet6 ([0-9a-f:]+)/\d+ scope global', addr_output)
            if match:
                return match.group(1)
        except subprocess.CalledProcessError:
            continue
    return None


if __name__ == '__main__':
    zone_id = os.getenv('CF_Zone_ID')
    api_key = os.getenv('CF_api_key')

    current_ipv4 = requests.get('https://api.ipify.org').text
    current_ipv6 = get_interface_ipv6()
    print('ipv4:', current_ipv4)
    print('ipv6:', current_ipv6)

    update_dns_record(zone_id, api_key, current_ipv4, current_ipv6)
    print('='* 30)


# @reboot { printf "\%s: \n" "$(date "+\%F \%T")"; /usr/bin/python3 /root/DDNS/ddns_cf.py ; } >> /root/DDNS/ddns_cf.log 2>&1