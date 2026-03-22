import os
import shlex
import subprocess
import sys
from pathlib import Path


def load_env(base_dir):
    print('->> Loading .env to sys env, manually...')

    env_path = base_dir / '.env'
    if not env_path.exists():
        raise FileNotFoundError(f'Missing env file: {env_path}')

    env_lines = env_path.read_text(encoding='utf-8').splitlines()
    for raw_line in env_lines:
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ[key] = value.strip().strip("'").strip('"')

    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    os.environ['UBUNTU_FRONTEND'] = 'noninteractive'

    print('--- .env loaded to sys environ.')


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def run_command(command, error_message, cwd=None):
    printout = env_flag('CMD_DETAIL_OUTPUT', True)
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=os.environ,
        )
    except Exception as exc:
        if printout:
            print('-- E2:', str(exc))
        sys.exit(1)

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    if printout:
        for stream_output in (stdout, stderr):
            if not stream_output:
                continue
            for line in stream_output.splitlines():
                if any(token in line for token in (
                    '(Reading database',
                    'Selecting previously unselected package',
                    'Preparing to unpack',
                    'Unpacking',
                    'inflating:',
                )):
                    continue
                print(line)

    if process.returncode != 0:
        if printout:
            print('-- E1:', error_message)
        return False, stdout, stderr

    return True, stdout, stderr


class Utility:
    def __init__(self, supported_platform, server_mapping, package_mapping, xray_mapping, github_repos) -> None:
        self.supported_platform = supported_platform
        self.server_mapping = server_mapping
        self.package_mapping = package_mapping
        self.xray_mapping = xray_mapping
        self.github_repos = github_repos

    def get_input_variable(self, setup_git_clone):
        platform = self.get_platform()

        confirm = self.prompt_confirmation('------------------------------\nShow script command detail?', False)
        os.environ['CMD_DETAIL_OUTPUT'] = 'show' if confirm else 'none'

        while True:
            print('------------------------------\nSelect a SERVER config pack:')
            for index, server_pack in enumerate(self.server_mapping):
                print(f"{index + 1}: {server_pack['name']} - {server_pack['domain']}")
            try:
                server_choice = int(input('------------------------------\nSelect a server to continute: '))
                if 1 <= server_choice <= len(self.server_mapping):
                    server_pack = self.server_mapping[server_choice - 1]
                    server = server_pack['name']
                    domains = server_pack['domain']
                    print(f'--- SERVER config pack selected: {server} - {domains}...')
                    break
                print('Invalid choice, try again.')
            except ValueError:
                print('Invalid input: please enter a number.')

        os.environ['ACME_ISSUE_CRETS'] = 'True' if self.prompt_confirmation(
            '------------------------------\nTry issue certs for this/those domain names?',
            True,
        ) else 'False'

        while True:
            print('------------------------------\nSelect a Package with NGINX config type:')
            for key, value in self.package_mapping.items():
                print(f'{key}: {value}')
            try:
                package_choice = int(input('------------------------------\nSelect a package to continute: '))
                if package_choice in self.package_mapping:
                    print(f'--- Package with NGINX selected: {self.package_mapping[package_choice]}...')
                    break
                print('Invalid choice, try again.')
            except ValueError:
                print('Invalid input: please enter a number.')

        os.environ['AUTO_INSTALL_PACKAGES'] = 'True' if self.prompt_confirmation(
            '------------------------------\nAutomatically install included packages?',
            True,
        ) else 'False'

        while True:
            print('------------------------------\nSelect XRAY config type:')
            for key, value in self.xray_mapping.items():
                print(f'{key}: {value}')
            try:
                xray_choice = int(input('------------------------------\nSelect XRAY config type to continute: '))
                if xray_choice in self.xray_mapping:
                    print(f'--- XRAY config type selected: {self.xray_mapping[xray_choice]}...')
                    break
                print('Invalid choice, try again.')
            except ValueError:
                print('Invalid input: please enter a number.')

        setup_git_clone.select_repos()
        return platform, server, domains, package_choice, xray_choice

    def prompt_confirmation(self, prompt, default=False):
        valid_choices = {'y': True, 'yes': True, 'n': False, 'no': False}
        choice_str = '(Y/n)' if default else '(y/N)'

        while True:
            value = input(f'{prompt} {choice_str} ').strip().lower()
            if value == '':
                return default
            if value in valid_choices:
                return valid_choices[value]
            print('Invalid input, try again.')

    def check_config_exsits(self, file_path, content):
        try:
            return content in Path(file_path).read_text()
        except FileNotFoundError:
            return False

    def get_platform(self):
        try:
            lines = Path('/etc/os-release').read_text().splitlines()
        except FileNotFoundError:
            print('Unrecognized platform, exit.')
            sys.exit(1)

        info = {}
        for line in lines:
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            info[key] = shlex.split(value)[0] if value else ''

        platform_id = info.get('ID', '').lower()
        for platform in self.supported_platform:
            if platform.lower() in platform_id:
                return platform

        print(f'Unsupported platform {platform_id}, add platform to supported list and test.')
        sys.exit(1)
