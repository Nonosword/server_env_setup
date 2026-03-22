import os
import subprocess
import sys
from pathlib import Path

from src.utility import env_flag, run_command


class InstallSysComponents:
    def __init__(self, package_root, venv_path, domains) -> None:
        self.venv_path = venv_path
        self.package_root = package_root
        self.domains = domains

    def start_functions(self):
        return {
            'apt_runs': self.apt_install_requirements(),
            'create_venv': self.create_virtual_env(self.venv_path),
            'acme.sh': self.setup_acme_cert(),
        }

    @staticmethod
    def apt_install_requirements(apt_packages=None):
        print('->> Installing apt-get environment requirements...')

        if apt_packages:
            print(f'--> Installing custom apt packages: {apt_packages}...')
            success, _, _ = run_command(
                ['sudo', 'apt-get', 'install', '-y', *apt_packages],
                f"Failed to install {' '.join(apt_packages)}",
            )
            return success

        apt_commands = [
            ['sudo', 'apt-get', 'clean', 'all'],
            ['sudo', 'apt-get', 'update'],
            ['sudo', 'apt-get', 'upgrade', '-y', '-o', 'Dpkg::Options::="--force-confdef"', '-o', 'Dpkg::Options::="--force-confold"'],
            ['sudo', 'apt-get', 'autoremove', '-y'],
            ['sudo', 'apt-get', 'install', '-y', 'curl', 'vim', 'git', 'python3.11-venv', 'unzip', 'nginx', 'mariadb-server', 'libpam-google-authenticator'],
        ]
        all_success = True
        for cmd in apt_commands:
            success, _, _ = run_command(cmd, f"Failed to run {' '.join(cmd)}")
            all_success = all_success and success
        return all_success

    @staticmethod
    def create_virtual_env(venv_path):
        print(f'->> Creating python virtual env to {venv_path}')
        if not venv_path.exists():
            run_command(['sudo', sys.executable, '-m', 'venv', venv_path], 'Unable to create virtual environment')
            print(f'--- Python venv created: {venv_path}...')

        venv_python = venv_path / 'bin' / 'python'
        success, _, _ = run_command([venv_python, '-m', 'pip', 'install', 'requests'], 'Failed to install pip requests')
        return venv_python if success else False

    def setup_acme_cert(self):
        print('->> Installing and setup acme.sh...')

        eab_kid = os.getenv('EAB_KID')
        eab_hmac_key = os.getenv('EAB_KEY')
        subprocess.run('curl https://get.acme.sh | sh -s', shell=True, check=True, text=True)

        commands = [
            [f'{self.package_root}/.acme.sh/acme.sh', '--upgrade', '--auto-upgrade'],
            [f'{self.package_root}/.acme.sh/acme.sh', '--set-default-ca', '--server', 'zerossl'],
            [f'{self.package_root}/.acme.sh/acme.sh', '--register-account', '--server', 'zerossl', '--eab-kid', eab_kid, '--eab-hmac-key', eab_hmac_key],
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")

        if not env_flag('ACME_ISSUE_CRETS'):
            print('--- Skipping issue certificates...')
            return None

        for domain in self.domains:
            print(f'--> Issuing certificates for {domain}...')
            os.environ['CF_Zone_ID'] = os.getenv(f'CF_Zone_ID_{domain}')
            cert_path = Path('/usr/local/nginx/conf/ssl/') / domain
            cert_path.mkdir(parents=True, exist_ok=True)

            commands = [
                [f'{self.package_root}/.acme.sh/acme.sh', '--issue', '--force', '--dns', 'dns_cf', '-d', domain, '-d', f'*.{domain}'],
                [f'{self.package_root}/.acme.sh/acme.sh', '--install-cert', '-d', domain, '--key-file', f'{cert_path}/{domain}.key', '--fullchain-file', f'{cert_path}/fullchain.cer'],
            ]
            for cmd in commands:
                run_command(cmd, f"Failed to run {' '.join(cmd)}")

        return True
