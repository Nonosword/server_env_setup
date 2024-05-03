import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from src.utility import run_command
from src.install_components import InstallSysComponents

# TODO separate package requirement installation from 'install_components' to each package;
# TODO for python package, create custom venv, and install requirement.txt
class InstallPackages:
    def __init__(self, utility, package_choice):
        self.utility = utility
        self.package_choice = package_choice

        self.wwwroot = Path('/home/wwwroot')
        self.wwwroot.mkdir(parents=True, exist_ok=True)

        nextcloud_url = 'https://download.nextcloud.com/server/releases/latest.zip'
        wordpress_url = 'https://wordpress.org/latest.zip'

        php_requires = ['php-fpm', 'php-xml', 'php-mbstring', 'php-gd', 'php-curl', 'php-zip', 'php-mysql']
        # the different package combination and nginx config is defined here.
        
        self.package_functions = {
            1: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.install_wget_package, ['nextcloud', nextcloud_url, self.wwwroot, php_requires])
            ],
            2: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.install_wget_package, ['nextcloud', nextcloud_url, self.wwwroot, php_requires]),
                ('chatgpt_web', self.install_chatgpt_web, [])
            ],
            3: [
                ('xray_core', self.install_xray_core, []),
                ('wordpress', self.install_wget_package, ['wordpress', wordpress_url, self.wwwroot, php_requires])
            ]
        }


    def start_functions(self):
        package_setup = self.package_functions.get(self.package_choice, [])
        results = {}
        for key, func, args in package_setup:
            results[key] = func(*args)
        
        shutil.chown(self.wwwroot, user='www-data', group='www-data')
        os.chmod(self.wwwroot, 0o755)
        return results


    def install_xray_core(self):
        print("->> Installing xray_core...")

        script_url = "https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
        command = [f'bash -c "$(curl -L {script_url})" @ install -u root']
        subprocess.run(command, check=True, text=True, shell=True)

        return True


    # this can be used for any package installed using the wget unpack method.
    def install_wget_package(self, package, url, path, apt_requires):
        print(f"->> Installing {package} from {url}")

        filename = urlparse(url).path.split('/')[-1]
        file_path = path / filename
        os.unlink(file_path) if os.path.isfile(file_path) else None  # fail safe

        print(f"--> Downloading {package} {filename}...")
        run_command(['wget', '-nv', url, '-P', path], f"Failed to download {package}")
        print(f"--> Unzipping {package} {filename}...")
        run_command(['unzip', '-n', '-q', file_path, '-d', path], f"Failed to unzip {package} file")
        # Attention! This will not overwrite existing files, otherwise use '-o' instead of '-n'.

        print(f"--> Removing {package} {filename}...")
        os.unlink(file_path)

        success = InstallSysComponents.apt_install_requirements(apt_requires)

        if package == 'nextcloud':
            print(f"--- Creating nextcloud data dir...")
            nextcloud_data_path = path / 'nextcloud' / 'data'
            nextcloud_data_path.mkdir(parents=True, exist_ok=True)

        return True


    # Source Repo: https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.
    def install_chatgpt_web(self):
        if not self.install_docker():
            print("--- docker is not installed properly, skiping...")
            return
        
        image_name = 'yidadaa/chatgpt-next-web'
        openai_api_key = os.getenv('OPENAI_API_KEY')
        passcode = os.getenv('WEBCHAT_PASSCODE')
        print(f"->> Installing docker {image_name}...")

        _, stdout, _ = run_command(['sudo', 'docker', 'ps', '-q', '--filter', f"ancestor={image_name}"], "Unable to check docker process list")
        if stdout:
            print(f"--- {image_name} is already running.")
        else:
            # Remember to set your key to sys env or .env.
            commands = [
                ['sudo', 'docker', 'pull', image_name],
                ['sudo', 'docker', 'run', '-d', '-p', '3000:3000', '-e', f'OPENAI_API_KEY={openai_api_key}', '-e', f'CODE={passcode}', 'yidadaa/chatgpt-next-web'],
            ]
            for cmd in commands:
                run_command(cmd, f"Failed to run {' '.join(cmd)}")

        return True


    # Remember to set your keys to sys env or .env file.
    def install_docker(self):
        print("->> Installing docker CE...")

        gpg_path = '/usr/share/keyrings/docker-archive-keyring.gpg'
        platform = self.utility.get_platform()
        if platform == 'Debian':
            docker_package = 'https://download.docker.com/linux/debian'
        elif platform == 'Ubuntu':
            docker_package = 'https://download.docker.com/linux/ubuntu'
        else:
            print("Platform not supported")
            return False

        print(f"--> Installing docker requirements -> {platform}...")
        run_command(['sudo', 'apt-get', 'install', '-y', 'apt-transport-https', 'ca-certificates', 'gnupg', 'lsb-release'], "Failed to install prerequisites.")

        print("--> Installing docker GPG KEY...")
        curl_output = subprocess.check_output(['sudo', 'curl', '-fsSL', f'{docker_package}/gpg'])
        subprocess.run(['sudo', 'gpg', '--dearmor', '-o', gpg_path], input=curl_output, check=True)

        print("--> Adding docker dpkg sources...")
        _, architecture, _ = run_command(['sudo', 'dpkg', '--print-architecture'], "Failed to run dpkg --print-architecture")
        _, release, _ = run_command(['sudo', 'lsb_release', '-cs'], "Failed to run lsb_release -cs")
        docker_list_content = f"deb [arch={architecture.strip()} signed-by={gpg_path}] {docker_package} {release.strip()} stable"
        Path('/etc/apt/sources.list.d/docker.list').write_text(docker_list_content)

        print("--> Installing docker CE using apt-get...")
        docker_commands = [
            ['sudo', 'apt-get', 'update', '-y'],
            ['sudo', 'apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io']
        ]
        all_success = True
        for cmd in docker_commands:
            success, _, _ = run_command(cmd, f"Failed to run {' '.join(cmd)}")
            if not success:
                all_success = False
                continue

        return all_success
