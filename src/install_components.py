import os
import sys
import subprocess
from pathlib import Path

from src.utility import run_command


class InstallSysComponents:
    def __init__(self, package_root, venv_path, domains) -> None:
        self.venv_path = venv_path
        self.package_root = package_root
        self.domains = domains


    def start_functions(self):
        results = {
            'apt_runs': self.apt_install_requirements(),
            'create_venv': self.create_virtual_env(self.venv_path),
            'acme.sh': self.setup_acme_cert()
        }
        return results


    @staticmethod
    def apt_install_requirements(packages=None):
        # when called by other function, use 'packages' as a list, like ['curl', 'vim', 'git'].
        print("->> Installing apt-get environment requirements...")

        if packages:
            print("--> Installing custom apt packages...")

            package_str = ' '.join(packages)
            success, _, _ = run_command(['sudo', 'apt-get', 'install', '-y', package_str], f"Failed to install {package_str}")
            return True if success else False


        # Interrupting the apt-get process may cause corruption of the dpkg database. If necessary, run "sudo dpkg --configure -a" to repair it.
        apt_commands = [
            ['sudo', 'apt-get', 'clean', 'all'],
            ['sudo', 'apt-get', 'update'],
            ['sudo', 'apt-get', 'upgrade', '-y', '-o', 'Dpkg::Options::="--force-confdef"', '-o', 'Dpkg::Options::="--force-confold"'],
            ['sudo', 'apt-get', 'autoremove', '-y'],
            ['sudo', 'apt-get', 'install', '-y', 'curl', 'vim', 'git', 'python3.11-venv', 'unzip', 'nginx', 'mariadb-server', 'libpam-google-authenticator']
        ]
        all_success = True
        for cmd in apt_commands:
            success, _, _ = run_command(cmd, f"Failed to run {' '.join(cmd)}")
            if not success:
                all_success = False
                continue

        return all_success


    @staticmethod
    def create_virtual_env(venv_path):
        # Well, there are many reasons to create a python venv.
        # This could be called by 'install_package' to create custom venv.
        print(f"->> Creating python virtual env to {venv_path}")

        if not venv_path.exists():
            run_command(['sudo', sys.executable, '-m', 'venv', venv_path], "Unable to create virtual environment")
            print(f"--- Python venv created: {venv_path}...")

        venv_python = venv_path / 'bin' / 'python'
        success, _, _ = run_command([venv_python, '-m', 'pip', 'install', 'requests'], "Failed to install pip requests")
        return venv_python if success else False


    def setup_acme_cert(self):
        # Usage: acme.sh + zerossl + cloudflare.
        # Thank them for promoting a free Internet.
        # 'eab_kid' and 'eab_hmac_key' can be obtained from zerossl website.
        print("->> Installing and setup acme.sh...")

        eab_kid = os.getenv('EAB_KID')
        eab_hmac_key = os.getenv('EAB_KEY')

        acme_sh = subprocess.check_output(['curl', '-sSL', 'https://get.acme.sh']).decode('utf-8')
        subprocess.run(['sh'], input=acme_sh, text=True)

        commands = [
            [f'{self.package_root}/.acme.sh/acme.sh', '--upgrade', '--auto-upgrade'],
            [f'{self.package_root}/.acme.sh/acme.sh', '--set-default-ca', '--server', 'zerossl'],
            [f'{self.package_root}/.acme.sh/acme.sh', '--register-account', '--server', 'zerossl', '--eab-kid', eab_kid, '--eab-hmac-key', eab_hmac_key],
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")

        # for domain in self.domains:
        # # This could take a while, be patient.
        # # Issue certs and install them to their own path for each domain under the server you selected.
        #     print(f"--> Issuing certificates for {domain}...")
            
        #     os.environ['CF_Zone_ID'] = os.getenv(f'CF_Zone_ID_{domain}')
        #     cert_path = Path('/usr/local/nginx/conf/ssl/') / domain
        #     cert_path.mkdir(parents=True, exist_ok=True)

        #     commands = [
        #         [f'{self.package_root}/.acme.sh/acme.sh', '--issue', '--force', '--dns', 'dns_cf', '-d', domain, '-d', f'*.{domain}'],
        #         [f'{self.package_root}/.acme.sh/acme.sh', '--install-cert', '-d', domain, '--key-file', f'{str(cert_path)}/{domain}.key', '--fullchain-file', f'{str(cert_path)}/fullchain.cer'],
        #     ]
        #     for cmd in commands:
        #         run_command(cmd, f"Failed to run {' '.join(cmd)}")

        return True
