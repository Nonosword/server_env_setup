import os
import re
import json
import shutil
import subprocess
from pathlib import Path

from src.utility import run_command


class UpdateConfig:
    def __init__(self, base_dir, package_choice, xray_choice, server, domains, php_v):
        self.base_dir = base_dir
        self.package_choice = package_choice
        self.xray_choice = xray_choice
        self.server = server
        self.domain = domains[0]
        self.php_v = php_v


    def start_functions(self):
        results = {
            'enable_bbr': self.enable_bbr(),
            'update_php_config': self.update_php_config(),
            'create_vimrc': self.create_vimrc(),
            'move_addons': self.move_addons(),
            'replace_config': self.replace_config()
        }
        return results


    def enable_bbr(self):
        print("->> Configuring BBR and sysctl.conf...")
        config_lines = [
            "net.core.default_qdisc = fq\n",
            "net.ipv4.tcp_congestion_control = bbr\n"
        ]

        stdout = subprocess.check_output(['sudo', 'sysctl', '-p']).decode()
        if all(line in stdout for line in config_lines):
            print("--- BBR is already enabled")
            return
        
        with Path('/etc/sysctl.conf').open('a', encoding='utf-8') as f:
            f.writelines(config_lines)
        run_command(['sudo', 'sysctl', '-p'], "Failed to reload sysctl configuration")
        print("--- BBR enabled and sysctl reloaded")


    def update_php_config(self): # for small vps
        print("->> Updating php configs...")

        updates = {
            'pm = dynamic': 'pm = ondemand',
            'pm.max_children = ': 'pm.max_children = 4',
            'pm.start_servers = ': 'pm.start_servers = 1',
            'pm.min_spare_servers = ': 'pm.min_spare_servers = 1',
            'pm.max_spare_servers = ': 'pm.max_spare_servers = 2',
            'pm.process_idle_timeout = ':'pm.process_idle_timeout = 10s;',
            'pm.max_requests = ': 'pm.max_requests = 200',

            'memory_limit = ': 'memory_limit = 64M',
            'upload_max_filesize = ': 'upload_max_filesize = 2M',
            'post_max_size = ': 'post_max_size = 8M',
            'max_execution_time = ': 'max_execution_time = 30',
            'max_input_time = ': 'max_input_time = 30',
            'opcache.enable = ': 'opcache.enable = 1',
            'opcache.memory_consumption = ': 'opcache.memory_consumption = 64',
            'opcache.interned_strings_buffer = 8': 'opcache.interned_strings_buffer = 8',
            'opcache.max_accelerated_files = 4000': 'opcache.max_accelerated_files = 4000',
            'opcache.validate_timestamps = 1': 'opcache.validate_timestamps = 1',
            'opcache.revalidate_freq = 2': 'opcache.revalidate_freq = 2',
        }

        config_paths = [
            Path(f'/etc/php/{self.php_v}/fpm/pool.d/www.conf'),
            Path(f'/etc/php/{self.php_v}/fpm/php.ini'),
            Path(f'/etc/php/{self.php_v}/cli/php.ini')
        ]

        for config_path in config_paths:
            lines = config_path.read_text().splitlines()

            new_content = []
            for line in lines:
                for old, new in updates.items():
                    if old in line:
                        line = new
                        break
                new_content.append(line)

            config_path.write_text('\n'.join(new_content) + '\n')
            print(f"--- {config_path} updated.")


    def create_vimrc(self):
        print("->> Creating .vimrc config...")

        vimrc = """
set mouse-=a
set tabstop=4
set shiftwidth=4
set expandtab
syntax on
colorscheme default
au BufRead,BufNewFile *.conf set syntax=sh
"""
        vimrc_path = Path('~/.vimrc').expanduser()
        with vimrc_path.open('a', encoding='utf-8') as f:
            f.write(f"\n{vimrc}\n")
        print(f"--- vim config insert into {vimrc_path}.")


    def move_addons(self):
        addon_path = self.base_dir / 'addons'
        target_path = Path('~/addons').expanduser()
        target_env = target_path / '.env'
        shutil.copytree(addon_path, target_path, dirs_exist_ok=True)

        zone_id = os.getenv(f'CF_Zone_ID_{self.domain}') # only MAIN domain is used
        api_key = os.getenv(f'CF_api_key_{self.domain}') # only MAIN domain is used
        
        with target_env.open('w', encoding='utf-8') as f:
            f.write(f'CF_Zone_ID={zone_id}\n')
            f.write(f'CF_api_key={api_key}\n')

        shutil.chown(target_path, user='root', group='root')
        os.chmod(target_path, 0o755)
        os.chmod(target_env, 0o600)


    def replace_config(self):
        print("->> Replacing nginx & xray config...")

        self.source_paths = {
            1: {"type":"nginx", "choice":1, "source_path": self.base_dir / 'config'/ 'nginx_nextcloud.conf', 'target_name':'nginx.conf'},
            2: {"type":"nginx", "choice":2, "source_path": self.base_dir / 'config'/ 'nginx_nextcloud_chatgpt.conf', 'target_name':'nginx.conf'},
            3: {"type":"nginx", "choice":3, "source_path": self.base_dir / 'config'/ 'location_config.conf', 'target_name':'location_config.conf'},
            4: {"type":"nginx", "choice":3, "source_path": self.base_dir / 'config'/ 'nginx_multi_locations.conf', 'target_name':'nginx.conf'},
            5: {"type":"xray", "choice":1, "source_path": self.base_dir / 'config'/ 'xray_xtls.json', 'target_name':'config.json'},
            6: {"type":"xray", "choice":2, "source_path": self.base_dir / 'config'/ 'xray_reality.json', 'target_name':'config.json'},
        }
        nginx_target_path = Path('/etc/nginx/')
        xray_target_path = Path('/usr/local/etc/xray/')

        self.update_config("nginx", self.package_choice, nginx_target_path)
        self.update_config("xray", self.xray_choice, xray_target_path)


    def update_config(self, type, choice, target_path):
        selected_config = [config for config in self.source_paths.values() if config["type"] == type and config["choice"] == choice]
        for config in selected_config:
            source_path = config["source_path"]
            target_name = config["target_name"]
            target_file = target_path / target_name

            if not target_file.exists():
                print(f"--> {target_file} does not exists, creating new")
                target_file.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy(source_path, target_file)
            print(f"--- {source_path} -> {target_file}")

            print("--> Replacing yourdomainname with real domain name...")
            content = target_file.read_text()
            new_content = content.replace('yourdomainname', self.domain) # only MAIN domain is used
            target_file.write_text(new_content)

            if type == 'xray':
                print("--> Removing single or multi-line comments in json files...")
                content = target_file.read_text(encoding='utf-8')
                cleaned_content = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.S)
                target_file.write_text(cleaned_content, encoding='utf-8')

                print("--> Adding clients for Xray json...")
                xray_clients_json = os.getenv('XRAY_CLIENTS')
                xray_clients = json.loads(xray_clients_json)
                server_clients = xray_clients.get(self.server, [])
                with target_file.open('r', encoding='utf-8') as file:
                    data = json.load(file)
                for i in data['inbounds']:
                    i['settings']['clients'] = server_clients

                with target_file.open('w', encoding='utf-8') as file:
                    json.dump(data, file, indent=4)

                if self.xray_choice == 2:
                    print("--> Adding REALITY configs...")
                    xray_reality_dest = os.getenv('XRAY_REALITY_DEST') 
                    xray_server_name = os.getenv('XRAY_SERVER_NAME') 
                    xray_reality_key = os.getenv('XRAY_REALITY_KEY') 
                    xray_shortids = os.getenv('XRAY_shortIds') 

                    with target_file.open('r', encoding='utf-8') as file:
                        data = json.load(file)
                    for i in data['inbounds']:
                        settings = i['streamSettings']['realitySettings']
                        settings['dest'] = xray_reality_dest
                        settings['serverNames'] = json.loads(xray_server_name)
                        settings['privateKey'] = xray_reality_key
                        settings['shortIds'] = json.loads(xray_shortids)

                    with target_file.open('w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4)

