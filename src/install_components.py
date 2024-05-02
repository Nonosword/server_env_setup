import os
import sys
import subprocess
from pathlib import Path

from src.utility import run_command


class InstallSysComponents:
    def __init__(self, venv_path, domains) -> None:
        self.venv_path = venv_path
        self.domains = domains


    def start_functions(self):
        results = {
            'apt_runs': self.install_requirements(),
            'create_venv': self.create_virtual_env(),
            'acme.sh': self.setup_acme_cert()
        }
        return results


    def install_requirements(self):
        print("->> Installing apt environment requirements...")

        # Interrupting the apt process may cause corruption of the dpkg database. If necessary, run "sudo dpkg --configure -a" to repair it.
        commands = [
            ['sudo', 'apt', 'clean', 'all'],
            ['sudo', 'apt', 'update'],
            ['sudo', 'apt', 'upgrade', '-y', '-o', 'Dpkg::Options::="--force-confdef"', '-o', 'Dpkg::Options::="--force-confold"'],
            ['sudo', 'apt', 'autoremove', '-y'],
            ['sudo', 'apt', 'install', '-y', 'curl', 'vim', 'git', 'python3.11-venv', 'php-fpm', 'php-xml', 'php-mbstring', 'php-gd', 'php-curl', 'php-zip', 'php-mysql', 'unzip', 'nginx', 'mariadb-server', 'libpam-google-authenticator']
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")


    # Well, there are many reasons to create a python venv.
    def create_virtual_env(self):
        print("->> Creating python virtual env")

        venv_name = "appvenv"
        venv_path = self.venv_path / venv_name
        if not venv_path.exists():
            run_command(['sudo', sys.executable, '-m', 'venv', venv_path], "Unable to create virtual environment")
            print(f"--- Python venv created: {venv_path}...")

        # venv_python = venv_path / 'bin' / 'python'
        # run_command(['sudo', venv_python, '-m', 'pip', 'install', 'request', 'python-dotenv'], "Failed to install requirement.txt")

        return venv_path


    def setup_acme_cert(self):
        # Usage: acme.sh + zerossl + cloudflare.
        # Thank them for promoting a free Internet.
        # 'eab_kid' and 'eab_hmac_key' can be obtained from zerossl website.
        print("->> Installing and setup acme.sh...")

        eab_kid = os.getenv('EAB_KID')
        eab_hmac_key = os.getenv('EAB_KEY')
        user_path = os.path.expanduser('~')

        acme_sh = subprocess.check_output(['curl', '-sSL', 'https://get.acme.sh']).decode('utf-8')
        subprocess.run(['sh'], input=acme_sh, text=True)

        commands = [
            [f'{user_path}/.acme.sh/acme.sh', '--upgrade', '--auto-upgrade'],
            [f'{user_path}/.acme.sh/acme.sh', '--set-default-ca', '--server', 'zerossl'],
            [f'{user_path}/.acme.sh/acme.sh', '--register-account', '--server', 'zerossl', '--eab-kid', eab_kid, '--eab-hmac-key', eab_hmac_key],
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")

        for domain in self.domains:
        # This could take a while, be patient.
        # Issue certs and install them to their own path for each domain under the server you selected.
            print(f"--> Issuing certificates for {domain}...")
            
            os.environ['CF_Zone_ID'] = os.getenv(f'CF_Zone_ID_{domain}')
            cert_path = Path('/usr/local/nginx/conf/ssl/') / domain
            cert_path.mkdir(parents=True, exist_ok=True)

            commands = [
                [f'{user_path}/.acme.sh/acme.sh', '--issue', '--force', '--dns', 'dns_cf', '-d', domain, '-d', f'*.{domain}'],
                [f'{user_path}/.acme.sh/acme.sh', '--install-cert', '-d', domain, '--key-file', f'{str(cert_path)}/{domain}.key', '--fullchain-file', f'{str(cert_path)}/fullchain.cer'],
            ]
            for cmd in commands:
                run_command(cmd, f"Failed to run {' '.join(cmd)}")

