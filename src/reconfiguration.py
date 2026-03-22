import json
import os
import re
import shutil
from pathlib import Path

from src.utility import run_command


class UpdateConfig:
    def __init__(self, base_dir, package_choice, xray_choice, server, domains):
        self.base_dir = base_dir
        self.package_choice = package_choice
        self.xray_choice = xray_choice
        self.server = server
        self.domain = domains[0]
        self.php_v = self.detect_php_version()

    def start_functions(self):
        return {
            'enable_bbr': self.enable_bbr(),
            'update_php_config': self.update_php_config(),
            'create_vimrc': self.create_vimrc(),
            'move_addons': self.move_addons(),
            'replace_config': self.replace_config(),
        }

    @staticmethod
    def detect_php_version():
        success, stdout, _ = run_command(['php', '-v'], 'Failed to detect php version')
        if success and stdout:
            return '.'.join(stdout.split()[1].split('.')[:2])

        php_root = Path('/etc/php')
        if php_root.exists():
            versions = sorted(path.name for path in php_root.iterdir() if path.is_dir())
            if versions:
                return versions[-1]

        raise RuntimeError('Unable to detect installed PHP version.')

    def enable_bbr(self):
        print('->> Configuring BBR and sysctl.conf...')
        config_lines = [
            'net.core.default_qdisc = fq\n',
            'net.ipv4.tcp_congestion_control = bbr\n',
        ]
        sysctl_path = Path('/etc/sysctl.conf')
        current = sysctl_path.read_text(encoding='utf-8') if sysctl_path.exists() else ''
        if all(line.strip() in current for line in config_lines):
            print('--- BBR is already enabled')
            return True

        with sysctl_path.open('a', encoding='utf-8') as file:
            file.writelines(config_lines)
        run_command(['sudo', 'sysctl', '-p'], 'Failed to reload sysctl configuration')
        print('--- BBR enabled and sysctl reloaded')
        return True

    def update_php_config(self):
        print('->> Updating php configs...')
        updates = {
            'pm = dynamic': 'pm = ondemand',
            'pm.max_children = ': 'pm.max_children = 4',
            'pm.start_servers = ': 'pm.start_servers = 1',
            'pm.min_spare_servers = ': 'pm.min_spare_servers = 1',
            'pm.max_spare_servers = ': 'pm.max_spare_servers = 2',
            'pm.process_idle_timeout = ': 'pm.process_idle_timeout = 10s;',
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
            Path(f'/etc/php/{self.php_v}/cli/php.ini'),
        ]

        for config_path in config_paths:
            if not config_path.exists():
                print(f'--- Skipping missing php config: {config_path}')
                continue
            lines = config_path.read_text().splitlines()
            new_content = []
            for line in lines:
                for old, new in updates.items():
                    if old in line:
                        line = new
                        break
                new_content.append(line)
            config_path.write_text('\n'.join(new_content) + '\n')
            print(f'--- {config_path} updated.')
        return True

    def create_vimrc(self):
        print('->> Creating .vimrc config...')
        vimrc = '\n'.join([
            'set mouse-=a',
            'set tabstop=4',
            'set shiftwidth=4',
            'set expandtab',
            'syntax on',
            'colorscheme default',
            'au BufRead,BufNewFile *.conf set syntax=sh',
        ])
        try:
            vimrc_path = Path('~/.vimrc').expanduser()
            with vimrc_path.open('a', encoding='utf-8') as file:
                file.write(f'\n{vimrc}\n')
            print(f'--- vim config insert into {vimrc_path}.')
            return True
        except Exception as exc:
            print(exc)
            return False

    def move_addons(self):
        addon_path = self.base_dir / 'addons'
        target_path = Path('~/addons').expanduser()
        target_env = target_path / '.env'
        shutil.copytree(addon_path, target_path, dirs_exist_ok=True)

        zone_id = os.getenv(f'CF_Zone_ID_{self.domain}')
        api_key = os.getenv(f'CF_api_key_{self.domain}')
        with target_env.open('w', encoding='utf-8') as file:
            file.write(f'CF_Zone_ID={zone_id}\n')
            file.write(f'CF_api_key={api_key}\n')

        shutil.chown(target_path, user='root', group='root')
        os.chmod(target_path, 0o755)
        os.chmod(target_env, 0o600)
        return True

    def replace_config(self):
        print('->> Replacing nginx & xray config...')
        self.source_paths = {
            1: {'type': 'nginx', 'choice': 1, 'source_path': self.base_dir / 'config' / 'nginx_nextcloud.conf', 'target_name': 'nginx.conf'},
            2: {'type': 'nginx', 'choice': 2, 'source_path': self.base_dir / 'config' / 'nginx_nextcloud_chatgpt.conf', 'target_name': 'nginx.conf'},
            3: {'type': 'nginx', 'choice': 3, 'source_path': self.base_dir / 'config' / 'location_config.conf', 'target_name': 'location_config.conf'},
            4: {'type': 'nginx', 'choice': 3, 'source_path': self.base_dir / 'config' / 'nginx_multi_locations.conf', 'target_name': 'nginx.conf'},
            5: {'type': 'xray', 'choice': 1, 'source_path': self.base_dir / 'config' / 'xray_xtls.json', 'target_name': 'config.json'},
            6: {'type': 'xray', 'choice': 2, 'source_path': self.base_dir / 'config' / 'xray_reality.json', 'target_name': 'config.json'},
        }
        self.update_config('nginx', self.package_choice, Path('/etc/nginx/'))
        self.update_config('xray', self.xray_choice, Path('/usr/local/etc/xray/'))
        return True

    def update_config(self, config_type, choice, target_path):
        selected_config = [config for config in self.source_paths.values() if config['type'] == config_type and config['choice'] == choice]
        for config in selected_config:
            source_path = config['source_path']
            target_file = target_path / config['target_name']

            if not target_file.exists():
                print(f'--> {target_file} does not exists, creating new')
                target_file.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy(source_path, target_file)
            print(f'--- {source_path} -> {target_file}')

            content = target_file.read_text(encoding='utf-8')
            target_file.write_text(content.replace('yourdomainname', self.domain), encoding='utf-8')

            if config_type != 'xray':
                continue

            print('--> Removing single or multi-line comments in json files...')
            content = target_file.read_text(encoding='utf-8')
            cleaned_content = re.sub(r'//.*?\n|/\*.*?\*/', '', content, flags=re.S)
            target_file.write_text(cleaned_content, encoding='utf-8')

            print('--> Adding clients for Xray json...')
            xray_clients = json.loads(os.getenv('XRAY_CLIENTS', '{}'))
            server_clients = xray_clients.get(self.server, [])
            data = json.loads(target_file.read_text(encoding='utf-8'))
            for inbound in data['inbounds']:
                inbound['settings']['clients'] = server_clients

            if self.xray_choice == 2:
                print('--> Adding REALITY configs...')
                for inbound in data['inbounds']:
                    settings = inbound['streamSettings']['realitySettings']
                    settings['dest'] = os.getenv('XRAY_REALITY_DEST')
                    settings['serverNames'] = json.loads(os.getenv('XRAY_SERVER_NAME', '[]'))
                    settings['privateKey'] = os.getenv('XRAY_REALITY_KEY')
                    settings['shortIds'] = json.loads(os.getenv('XRAY_shortIds', '[]'))

            target_file.write_text(json.dumps(data, indent=4), encoding='utf-8')
