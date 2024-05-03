import os
import json
from pathlib import Path

from src.utility import Utility
from src.apply_security import SafetyPractices
from src.install_components import InstallSysComponents
from src.install_packages import InstallPackages
from src.ssh_git_clone import SetupSSHGithub
from src.reconfiguration import UpdateConfig

from src.utility import load_env, run_command


package_mapping = {
    1: 'nginx + nextcloud', 
    2: 'nginx + nextcloud + chatgpt', 
    3: 'nginx + wp + multi path'
}
xray_mapping = {
    1: 'XTLS', 
    2: 'REALITY'
}


if __name__ == '__main__':
    supported_platform = ['Debian', 'Ubuntu']
    BASE_DIR = Path(__file__).resolve().parent
    load_env(BASE_DIR)
    package_root = Path('~/').expanduser()
    venv_path = package_root / 'appvenv'
    venv_python = venv_path / 'bin' / 'python'

    server_mapping = os.getenv('SERVER_MAPPING')
    server_mapping = json.loads(server_mapping)
    github_repos = os.getenv('GITHUB_REPOS')
    github_repos = json.loads(github_repos)


    setup_git_clone = SetupSSHGithub(package_root, github_repos, venv_python)
    
    utility = Utility(supported_platform, server_mapping, package_mapping, xray_mapping, github_repos)
    platform, server, domains, package_choice, xray_choice, selected_repos = utility.get_input_variable(setup_git_clone)

    print(">>> Secure system environment...")
    security_practices = SafetyPractices(server, utility)
    security_result = security_practices.start_functions()

    print(">>> Starting system dependency installation...")
    install_sys_comps = InstallSysComponents(package_root, venv_path, domains)
    syscomponents_result = install_sys_comps.start_functions()

    print(">>> Installing selected packages...")
    install_packages = InstallPackages(utility, package_choice)
    packages_result = install_packages.start_functions()

    print(">>> Setup Git@Github SSH Connection")
    gitclone_result = setup_git_clone.start_functions()

    _, php_v, _ = run_command(['php', '-v'], "Failed to run print php version.")
    php_v = ".".join(php_v.split()[1].split('.')[:2])

    print(">>> Updating configs...")
    update_configs = UpdateConfig(BASE_DIR, package_choice, xray_choice, server, domains, php_v)
    reconfiguration_result = update_configs.start_functions()

    # print(">>> Setting up Mysql...")
    # run'sudo mysql_secure_installation' manually

    print(">>> Restarting services...")
    run_command(['sudo', 'systemctl', 'restart', 'nginx'], "Failed to restart nginx")
    run_command(['sudo', 'systemctl', 'restart', 'xray'], "Failed to restart xray")
    run_command(['sudo', 'systemctl', 'restart', f'php{php_v}-fpm'], "Failed to restart php-fpm")

    print(">>> Deployment completed.")

    # TODO Collect True, False, None status from each function for detailed process management.
    # Run the entire script without interrupting, and auto retry functions marked by False Status.
    print(security_result)
    print(syscomponents_result)
    print(packages_result)
    print(gitclone_result)
    print(reconfiguration_result)
    