import os
import sys
import select
import subprocess
from pathlib import Path



def load_env(base_dir):
    # Load local .env manually, as python-dotenv needs to be installed into a venv, which not right now.
    print("->> Loading .env to sys env, manually...")

    env_path = base_dir / '.env'
    env_lines = env_path.read_text(encoding='utf-8').splitlines()
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key] = value.strip("'").strip('"')

    os.environ['DEBIAN_FRONTEND']='noninteractive'
    os.environ['UBUNTU_FRONTEND']='noninteractive'

    print("--- .env loaded to  sys environ.")


def run_command(command, error_message, input=None):
    printout = os.getenv('CMD_DETAIL_OUTPUT', 'show') == 'show'
    try:       
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ)

        stdout_content = []
        stderr_content = []
        # Set the stdout and stderr output streams as-is
        while True:
            reads = [process.stdout.fileno(), process.stderr.fileno()]
            ret = select.select(reads, [], [])

            for fd in ret[0]:
                if fd == process.stdout.fileno():
                    read = process.stdout.readline()
                    if read:
                        stdout_content.append(read.strip())
                        if printout and "(Reading database" not in read and "Selecting previously unselected package" not in read and "Preparing to unpack" not in read and "Unpacking" not in read and "inflating:" not in read:
                            print(read.strip())
                elif fd == process.stderr.fileno():
                    read = process.stderr.readline()
                    if read:
                        stderr_content.append(read.strip())
                        if printout:
                            print(read.strip())

            # Check whether the caller's process has ended. different between 'Popen' and 'run'
            if process.poll() is not None:
                break

        stdout, stderr = process.communicate(input=input)
        if stdout:
            stdout_content.append(stdout.strip())
        if stderr:
            stderr_content.append(stderr.strip())

        # Return the stdout and stderr feedback to caller:
        if process.returncode != 0:
            if printout:
                print("-- E1:", error_message)
            return '\n'.join(stdout_content), '\n'.join(stderr_content)

        return '\n'.join(stdout_content), '\n'.join(stderr_content)

    except Exception as e:
        if printout:
            print("-- E2:", str(e))
        sys.exit(1)



class Utility():
    def __init__(self, server_mapping, package_mapping, xray_mapping, github_repos) -> None:
        self.server_mapping = server_mapping
        self.package_mapping = package_mapping
        self.xray_mapping = xray_mapping
        self.github_repos = github_repos


    def get_input_variable(self):
        # Continue looping until exiting manually, or an unexpected error occurs. 
        # SERVER hostname variable, use to check and setup server domains, xray configs, acme keys, ddns keys.

        # Set sys env to control run command output mode.
        confirm = self.prompt_confirmation("------------------------------\nShow script command detail?", True)
        if confirm:
            os.environ['CMD_DETAIL_OUTPUT'] = 'show'
        else:
            os.environ['CMD_DETAIL_OUTPUT'] = 'none'


        while True:
            print("------------------------------\nSelect a SERVER config pack:")
            for index, server_pack in enumerate(self.server_mapping):
                print(f"{index + 1}: {server_pack['name']} - {server_pack['domain']}")
            try:
                server_choice = int(input("------------------------------\nSelect a server to continute: "))
                if 0 <= server_choice -1 <= len(self.server_mapping):
                    server_pack = self.server_mapping[server_choice -1]
                    server = server_pack['name']
                    domains = server_pack['domain']
                    print(f"--- SERVER config pack selected: {server} - {domains}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")


        # Nginx config types, pre configured and easy to conbine and replace.
        while True:
            print("------------------------------\nSelect a Package with NGINX config type:")
            for key, value in self.package_mapping.items():
                print(f"{key}: {value}")
            try:
                package_choice = int(input("------------------------------\nSelect a package to continute: "))
                if package_choice in self.package_mapping:
                    print(f"--- Package with NGINX selected: {self.package_mapping[package_choice]}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")


        # Xray-core configs, pre configured.
        while True:
            print("------------------------------\nSelect XRAY config type:")
            for key, value in self.xray_mapping.items():
                print(f"{key}: {value}")
            try:
                xray_choice = int(input("------------------------------\nSelect XRAY config type to continute: "))
                if xray_choice in self.xray_mapping:
                    print(f"--- XRAY config type selected: {self.xray_mapping[xray_choice]}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")

        selected_repos = []
        while True:
            print("\n------------------------------\nGithub repo list: ")
            for index, repo in enumerate(self.github_repos):
                print(f"{index + 1}: {repo['name']}")

            try:
                repo_choice = int(input("------------------------------\nChoose a repo to clone list (0 to exit): "))
                if repo_choice == 0:
                    break
                elif 1 <= repo_choice <= len(self.github_repos):
                    repo = self.github_repos[repo_choice -1]
                    name = repo['name']
                    if repo_choice -1 in selected_repos:
                        print(f"--- repo <{name}> already in the list.")
                        continue
                    selected_repos.append(repo_choice -1)
                    print(f"--- repo <{name}> added to git clone list...\n")
                    print(selected_repos) # test

                    print("------------------------------\nCurrent git clone list: ")
                    for i in selected_repos:
                        repo = self.github_repos[i]
                        name = repo['name']
                        print(f"--- {name}")
                    continue

                else:
                    print("Invalid repo id")
            except ValueError:
                print("Invalid input: please enter a number.")

        return server, domains, package_choice, xray_choice, selected_repos


    def prompt_confirmation(self, prompt, default=False):
    # A confirmation "prompt" for double-checking high-risk actions.
        valid_choices = {
            'y': True,
            'yes': True,
            'n': False,
            'no': False,
        }

        choice_str = ''
        if default:
            choice_str = '(Y/n)'
        else:
            choice_str = '(y/N)'

        # Setting or not setting a default value results in different default actions.
        while True:
            value = input(f"{prompt} {choice_str} ").strip().lower()
            if value == '':
                return default
            if value in valid_choices:
                return valid_choices[value]
            print("Invalid input, try again.")


    def check_config_exsits(self, file_path, content):
    # To chekc whether WORDS in FILE.
        try:
            if content in Path(file_path).read_text():
                return True
        except FileNotFoundError:
            return False
        return False


    def get_platform(self):
        try:
            with Path('/etc/os-release').read_text() as f:
                lines = f.readlines()
                info = {line.split('=')[0]: line.split('=')[1].strip().replace('"', '') for line in lines}
            if 'debian' in info.get('ID', '').lower():
                return 'debian'
            elif 'ubuntu' in info.get('ID', '').lower():
                return 'ubuntu'
            else:
                return None
        except FileNotFoundError:
            return None
