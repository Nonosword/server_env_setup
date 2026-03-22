import json
import os
from pathlib import Path

from src.apply_security import SafetyPractices
from src.install_components import InstallSysComponents
from src.install_packages import InstallPackages
from src.reconfiguration import UpdateConfig
from src.ssh_git_clone import SetupSSHGithub
from src.utility import Utility, load_env, run_command


package_mapping = {
    1: 'nginx + nextcloud',
    2: 'nginx + nextcloud + chatgpt',
    3: 'nginx + wp + multi path',
}

xray_mapping = {
    1: 'XTLS',
    2: 'REALITY',
}


def initialize_paths():
    package_root = Path('~/').expanduser()
    venv_path = package_root / 'appvenv'
    venv_python = venv_path / 'bin' / 'python'
    return package_root, venv_path, venv_python


def read_sysparameters():
    supported_platform = ['Debian', 'Ubuntu']
    server_mapping = json.loads(os.getenv('SERVER_MAPPING', '[]'))
    github_repos = json.loads(os.getenv('GITHUB_REPOS', '[]'))
    return supported_platform, server_mapping, github_repos


def initialize_classes(base_dir):
    package_root, venv_path, venv_python = initialize_paths()
    supported_platform, server_mapping, github_repos = read_sysparameters()

    setup_git_clone = SetupSSHGithub(package_root, github_repos, venv_python)
    utility = Utility(supported_platform, server_mapping, package_mapping, xray_mapping, github_repos)
    platform, server, domains, package_choice, xray_choice = utility.get_input_variable(setup_git_clone)
    security_practices = SafetyPractices(server, utility)
    install_sys_comps = InstallSysComponents(package_root, venv_path, domains)
    install_packages = InstallPackages(platform, package_choice)
    update_configs = UpdateConfig(base_dir, package_choice, xray_choice, server, domains)

    return setup_git_clone, security_practices, install_sys_comps, install_packages, update_configs


if __name__ == '__main__':
    base_dir = Path(__file__).resolve().parent
    load_env(base_dir)

    setup_git_clone, security_practices, install_sys_comps, install_packages, update_configs = initialize_classes(base_dir)

    print('>>> Secure system environment...')
    security_result = security_practices.start_functions()
    print('>>> Starting system dependency installation...')
    syscomponents_result = install_sys_comps.start_functions()
    print('>>> Installing selected packages...')
    packages_result = install_packages.start_functions()
    print('>>> Setup Git@Github SSH Connection')
    gitclone_result = setup_git_clone.start_functions()
    print('>>> Updating configs...')
    reconfiguration_result = update_configs.start_functions()

    print('>>> Restarting services...')
    for service, error_message in (
        ('nginx', 'Failed to restart nginx'),
        ('xray', 'Failed to restart xray'),
        (f'php{update_configs.php_v}-fpm', 'Failed to restart php-fpm'),
    ):
        run_command(['sudo', 'systemctl', 'restart', service], error_message)

    print('>>> Deployment completed.')
    print(security_result)
    print(syscomponents_result)
    print(packages_result)
    print(gitclone_result)
    print(reconfiguration_result)
