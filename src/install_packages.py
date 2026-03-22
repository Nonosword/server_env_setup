import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from src.install_components import InstallSysComponents
from src.utility import env_flag, run_command


class InstallPackages:
    def __init__(self, platform, package_choice):
        self.platform = platform
        self.package_choice = package_choice
        self.wwwroot = Path('/home/wwwroot')
        self.wwwroot.mkdir(parents=True, exist_ok=True)

        nextcloud_url = 'https://download.nextcloud.com/server/releases/latest.zip'
        wordpress_url = 'https://wordpress.org/latest.zip'
        php_requires = ['php-fpm', 'php-xml', 'php-mbstring', 'php-gd', 'php-curl', 'php-zip', 'php-mysql']

        self.package_functions = {
            1: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.install_wget_package, ['nextcloud', nextcloud_url, self.wwwroot, php_requires]),
            ],
            2: [
                ('xray_core', self.install_xray_core, []),
                ('nextcloud', self.install_wget_package, ['nextcloud', nextcloud_url, self.wwwroot, php_requires]),
                ('chatgpt_web', self.install_chatgpt_web, []),
            ],
            3: [
                ('xray_core', self.install_xray_core, []),
                ('wordpress', self.install_wget_package, ['wordpress', wordpress_url, self.wwwroot, php_requires]),
            ],
        }

    def start_functions(self):
        if not env_flag('AUTO_INSTALL_PACKAGES'):
            print('--- Skipping package installation...')
            return None

        package_setup = self.package_functions.get(self.package_choice, [])
        results = {}
        for key, func, args in package_setup:
            results[key] = func(*args)

        print('->> Setting up wwwroot permissions...')
        for command in (
            ['sudo', 'chown', '-R', 'www-data', self.wwwroot],
            ['sudo', 'chmod', '-R', '755', self.wwwroot],
        ):
            run_command(command, '--- Failed to set permissions:')
        return results

    def install_xray_core(self):
        print('->> Installing xray_core...')
        script_url = 'https://github.com/XTLS/Xray-install/raw/main/install-release.sh'
        subprocess.run(f'bash -c "$(curl -L {script_url})" @ install -u root', check=True, text=True, shell=True)
        return True

    def install_wget_package(self, package, url, target_path, apt_requires):
        print(f'->> Installing {package} from {url}')
        parsed_url = Path(urlparse(url).path)
        filename = parsed_url.name
        ext = parsed_url.suffix[1:]
        file_path = target_path / filename

        if file_path.is_file():
            file_path.unlink()

        print(f'--> Downloading {package} {filename}...')
        run_command(['wget', '-nv', url, '-P', target_path], f'Failed to download {package}')

        if ext == 'zip':
            print(f'--> Unzipping {package} {filename}...')
            run_command(['unzip', '-n', '-q', file_path, '-d', target_path], f'Failed to unzip {package} file')
            print(f'--> Removing {package} {filename}...')
            file_path.unlink()

        success = InstallSysComponents.apt_install_requirements(apt_requires)
        if package == 'nextcloud':
            print('--- Creating nextcloud data dir...')
            (target_path / 'nextcloud' / 'data').mkdir(parents=True, exist_ok=True)

        return success

    def install_chatgpt_web(self):
        if not self.install_docker():
            print('--- docker is not installed properly, skiping...')
            return None

        image_name = 'yidadaa/chatgpt-next-web'
        openai_api_key = os.getenv('OPENAI_API_KEY')
        passcode = os.getenv('WEBCHAT_PASSCODE')
        print(f'->> Installing docker {image_name}...')

        _, stdout, _ = run_command(['sudo', 'docker', 'ps', '-q', '--filter', f'ancestor={image_name}'], 'Unable to check docker process list')
        if stdout:
            print(f'--- {image_name} is already running.')
            return True

        for cmd in (
            ['sudo', 'docker', 'pull', image_name],
            ['sudo', 'docker', 'run', '-d', '-p', '3000:3000', '-e', f'OPENAI_API_KEY={openai_api_key}', '-e', f'CODE={passcode}', image_name],
        ):
            run_command(cmd, f"Failed to run {' '.join(cmd)}")
        return True

    def install_docker(self):
        print('->> Installing docker CE...')
        gpg_path = '/usr/share/keyrings/docker-archive-keyring.gpg'
        if self.platform == 'Debian':
            docker_package = 'https://download.docker.com/linux/debian'
        elif self.platform == 'Ubuntu':
            docker_package = 'https://download.docker.com/linux/ubuntu'
        else:
            print('Platform not supported')
            return False

        print(f'--> Installing docker requirements -> {self.platform}...')
        run_command(['sudo', 'apt-get', 'install', '-y', 'apt-transport-https', 'ca-certificates', 'gnupg', 'lsb-release'], 'Failed to install prerequisites.')

        print('--> Installing docker GPG KEY...')
        curl_output = subprocess.check_output(['sudo', 'curl', '-fsSL', f'{docker_package}/gpg'])
        subprocess.run(['sudo', 'gpg', '--dearmor', '-o', gpg_path], input=curl_output, check=True)

        print('--> Adding docker dpkg sources...')
        _, architecture, _ = run_command(['sudo', 'dpkg', '--print-architecture'], 'Failed to run dpkg --print-architecture')
        _, release, _ = run_command(['sudo', 'lsb_release', '-cs'], 'Failed to run lsb_release -cs')
        Path('/etc/apt/sources.list.d/docker.list').write_text(
            f'deb [arch={architecture.strip()} signed-by={gpg_path}] {docker_package} {release.strip()} stable'
        )

        all_success = True
        for cmd in (
            ['sudo', 'apt-get', 'update', '-y'],
            ['sudo', 'apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'],
        ):
            success, _, _ = run_command(cmd, f"Failed to run {' '.join(cmd)}")
            all_success = all_success and success
        return all_success
