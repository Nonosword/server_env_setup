import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from src.utility import run_command


class InstallPackages:
    def __init__(self, package_choice, utility):
        self.package_choice = package_choice
        self.utility = utility

        self.wwwroot_path = Path('/home/wwwroot')
        self.wwwroot_path.mkdir(parents=True, exist_ok=True)

        self.nextcloud_url = 'https://download.nextcloud.com/server/releases/latest.zip'
        self.wordpress_url = 'https://wordpress.org/latest.zip'

        # the different package combination and nginx config is defined here.
        self.package_functions = {
            1: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.wget_wwwroot_package, ['nextcloud', self.nextcloud_url])
            ],
            2: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.wget_wwwroot_package, ['nextcloud', self.nextcloud_url]),
                ('chatgpt_web', self.install_chatgpt_web, [self.utility])
            ],
            3: [
                ('xray_core', self.install_xray_core, []),
                ('wordpress', self.wget_wwwroot_package, ['wordpress', self.wordpress_url])
            ]
        }


    def start_functions(self):
        package_setup = self.package_functions.get(self.package_choice, [])
        results = {}
        for key, func, args in package_setup:
            results[key] = func(*args)
        
        shutil.chown(self.wwwroot_path, user='www-data', group='www-data')
        os.chmod(self.wwwroot_path, 0o755)
        return results


    def install_xray_core(self):
        print("->> Installing xray_core...")

        script_url = "https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
        command = [f'bash -c "$(curl -L {script_url})" @ install -u root']
        subprocess.run(command, check=True, text=True, shell=True)


    # this can be used for any package installed using the wget unpack method.
    def wget_wwwroot_package(self, package, url):
        print(f"->> Installing {package} from {url}")

        filename = urlparse(url).path.split('/')[-1]
        file_path = self.wwwroot_path / filename
        os.unlink(file_path) if os.path.isfile(file_path) else None  # fail safe

        print(f"--> Downloading {package} {filename}...")
        run_command(['wget', url, '-P', self.wwwroot_path], f"Failed to download {package}")
        print(f"--> Unzipping {package} {filename}...")
        run_command(['unzip', '-n', file_path, '-d', self.wwwroot_path], f"Failed to unzip {package} file")
        # Attention! This will overwrite existing files, otherwise use '-n' instead of '-o'.
        print(f"--> Removing {package} {filename}...")
        os.unlink(file_path)
        
        if package == 'nextcloud':
            print(f"--- Creating nextcloud data dir...")
            nextcloud_data_path = self.wwwroot_path / 'nextcloud' / 'data'
            nextcloud_data_path.mkdir(parents=True, exist_ok=True)


    # Source Repo: https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.
    def install_chatgpt_web(self):
        if not self.install_docker():
            print("--- docker is not installed properly, skiping...")
            return
        
        image_name = 'yidadaa/chatgpt-next-web'
        openai_api_key = os.getenv('OPENAI_API_KEY')
        passcode = os.getenv('WEBCHAT_PASSCODE')
        print(f"->> Installing docker {image_name}...")

        stdout, _ = run_command(['sudo', 'docker', 'ps', '-q', '--filter', f"ancestor={image_name}"], "Unable to check docker process list")
        if stdout:
            print(f"--- {image_name} is already running.")
            return
        else:
            # Remember to set your key to sys env or .env.
            commands = [
                ['sudo', 'docker', 'pull', image_name],
                ['sudo', 'docker', 'run', '-d', '-p', '3000:3000', '-e', f'OPENAI_API_KEY={openai_api_key}', '-e', f'CODE={passcode}', 'yidadaa/chatgpt-next-web'],
            ]
            for cmd in commands:
                run_command(cmd, f"Failed to run {' '.join(cmd)}")


    # Remember to set your keys to sys env or .env file.
    def install_docker(self):
        print("->> Installing docker CE...")

        gpg_path = '/usr/share/keyrings/docker-archive-keyring.gpg'
        platform = self.utility.get_platform()
        if platform == 'debian':
            docker_package = 'https://download.docker.com/linux/debian'
        elif platform == 'ubuntu':
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
        architecture, _ = run_command(['sudo', 'dpkg', '--print-architecture'], "Failed to run dpkg --print-architecture")
        release, _ = run_command(['sudo', 'lsb_release', '-cs'], "Failed to run lsb_release -cs")
        docker_list_content = f"deb [arch={architecture.strip()} signed-by={gpg_path}] {docker_package} {release.strip()} stable"
        Path('/etc/apt/sources.list.d/docker.list').write_text(docker_list_content)

        print("--> Installing docker CE using apt-get...")
        run_command(['sudo', 'apt-get', 'update', '-y'], "Failed to update package index.")
        run_command(['sudo', 'apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'], "Failed to install Docker Engine.")

        return True

