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
    BASE_DIR = Path(__file__).resolve().parent
    load_env(BASE_DIR)

    server_mapping = os.getenv('SERVER_MAPPING')
    server_mapping = json.loads(server_mapping)
    github_repos = os.getenv('GITHUB_REPOS')
    github_repos = json.loads(github_repos)
    
    utility = Utility(server_mapping, package_mapping, xray_mapping, github_repos)
    server, domains, package_choice, xray_choice, selected_repos = utility.get_input_variable()

    print(">>> Secure system environment...")
    security_practices = SafetyPractices(server, utility)
    security_result = security_practices.start_functions()
    # TODO Collect True, False, None status from each function for detailed process management.
    # Run the entire script without interrupting, and auto retry functions marked by False Status.

    print(">>> Starting system dependency installation...")
    install_sys_comps = InstallSysComponents(Path('~/').expanduser(), domains)
    syscomponents_result = install_sys_comps.start_functions()

    print(">>> Installing selected packages...")
    install_packages = InstallPackages(package_choice, utility)
    packages_result = install_packages.start_functions()

    print(">>> Setup Git@Github SSH Connection")
    setup_git_clone = SetupSSHGithub(github_repos, selected_repos)
    gitclone_result = setup_git_clone.start_functions()

    php_v, _ = run_command(['php', '-v'], "Failed to run print php version.")
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
