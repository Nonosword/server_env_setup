import os
from pathlib import Path

from src.utility import run_command


class SetupSSHGithub():
    def __init__(self, package_root, github_repos, venv_python) -> None:
        print("->> Staring Github SSH key and private repo configuration...")
        self.package_root = package_root
        self.github_repos = github_repos
        self.venv_python = venv_python

        # new key and config will write to this file
        self.key_dir = Path('~/.ssh').expanduser()
        self.key_path = self.key_dir / 'gh_id_rsa'
        self.config_path = self.key_dir / 'config'


    def start_functions(self):
        ssh_checked = self.git_ssh_check()
        results = {
            'git_clone': self.git_clone_selected() if ssh_checked else False
        }

        return results


    def git_ssh_check(self):
        # Checking github via ssh, for git clone private repo.
        # skip ssh connetcion check if there;s no private repo on the list.
        all_public = all(repo['type'] == 'public' for repo in self.github_repos)
        ssh_checked = True if all_public else self.setup_git_ssh_conn()

        return ssh_checked


    def select_repos(self):
        ssh_checked = self.git_ssh_check()

        self.selected_repos = []
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
                    if repo_choice -1 in self.selected_repos:
                        print(f"--- repo <{name}> already in the list.")
                        continue
                    self.selected_repos.append(repo_choice -1)
                    print(f"--- repo <{name}> added to git clone list...\n")
                    print("------------------------------\nCurrent git clone list: ")
                    for i in self.selected_repos:
                        repo = self.github_repos[i]
                        name = repo['name']
                        print(f"--- {name}")
                    continue

                else:
                    print("Invalid repo id")
            except ValueError:
                print("Invalid input: please enter a number.")

        return self.selected_repos


    def git_clone_selected(self):
        all_success = True
        for repo in self.selected_repos:
            repo = self.github_repos[repo]
            name = repo['name']
            path = repo['path']

            print(f"->> Processing git clone <{name}>...")
            success, _, stderr = run_command(['git', 'clone', f'git@github.com:{path}.git', self.package_root / name], "") # Checking git feedback

            if "already exists" in stderr:
                print("--- Reop dir already exists, use 'git pull origin master/main' instead.\n")
                continue

            if not success:
                all_success = False

            # Auto install repo requirements, if exists.
            dep_success = self.install_dependencies(name)
            if not dep_success:
                all_success = False

        return all_success


    def install_dependencies(self, repo_name):
        repo_path = self.package_root / repo_name
        print(f"->> Looking for dependencies list in <{repo_path}>...")

        dependencies = [
            {
                'name': 'Python',
                'flag': 'requirements.txt',
                'command': [self.venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt']
            },
            {
                'name': 'JavaScript',
                'flag': 'package.json',
                'command': ['npm', 'install']
            },
        ]

        all_success = True
        for dep in dependencies:
            flag_file = repo_path / dep['flag']
            if flag_file.exists():
                print(f"--> Installing {dep['name']} dependencies...")
                success, _, _ = run_command(dep['command'], "", cwd=repo_path)
                if not success:
                    all_success = False
            
        return all_success


    # Checking ssh connection to github; 
    # or pin point a exist key to copy to target key file, 
    # or paste one into the cli.
    def setup_git_ssh_conn(self):
        while True:
            if self.check_ssh_connection():
                return True
            user_choice = int(input("""
------------------------------
Unable to SSH GitHub, choose:
-0- to skip for now. 
-1- to point a key path. 
-2- to manually typein a key.
Type your choice here: """))

            if user_choice == 0:
                return None
            elif user_choice == 1:
                # paste a vaild path like string '/root/.ssh/id_rsa'
                while True:
                    input_key_path = input("Type your exist key path here:")
                    if not Path(input_key_path).exists():
                        print("Invaild file path, or does't exist, try again.")
                        continue

                    self.handle_ssh_key(input_key_path)
                    if self.check_ssh_connection():
                        print("---SSH GitHub test pass")
                        return True
            elif user_choice == 2:
                self.handle_ssh_key()
                if self.check_ssh_connection():
                    print("---SSH GitHub test pass")
                    return True
            else:
                print("Invalid choice, try again.")


    def check_ssh_connection(self):
        print("--> Checking ssh git@github.com connection")

        _, _, stderr = run_command(['ssh', '-o', 'StrictHostKeyChecking=no', '-T', 'git@github.com'], "")
        if "successfully authenticated" in stderr:
            return True
        else:
            print("--- SSH connection test failed:", stderr)
            return False


    def handle_ssh_key(self, input_key_path=None):
        key_content = ""
        if input_key_path:
            key_content = Path(input_key_path).read_text()
        else:
            print("""
------------------------------
You have choosed to input key manually or key path privoded does not exists.
Input Github private key content below: (press Enter to finish): 
""")
            while True:
                line = input()
                if not line.strip():
                    break
                key_content += line + "\n"

        self.key_path.write_text(key_content)
        self.apply_ssh_config()


    # Adding new Host part to key config, or replace an exsit 'Host github.com' config part.
    def apply_ssh_config(self):
        key_config = f"""
Host github.com
    HostName github.com
    User git
    IdentityFile {self.key_path}
    IdentitiesOnly yes
""".strip() + '\n'

        config_content = self.config_path.read_text() if self.config_path.exists() else ""
        start_index = config_content.find("Host github.com")
        if start_index != -1:
            end_index = config_content.find("Host ", start_index + 1)
            if end_index == -1:
                end_index = len(config_content)
            config_content = config_content[:start_index] + key_config + config_content[end_index:]
        else:
            config_content += key_config
        self.config_path.write_text(config_content)

        os.chmod(self.key_dir, 0o700)
        os.chmod(self.key_path, 0o600)
