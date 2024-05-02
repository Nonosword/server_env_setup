import os
import sys
import json
import shutil
import select
import subprocess
from pathlib import Path
from urllib.parse import urlparse

package_mapping = {
    1: 'nginx + nextcloud', 
    2: 'nginx + nextcloud + chatgpt', 
    3: 'nginx + wp + multi path'
}
xray_mapping = {
    1: 'XTLS', 
    2: 'REALITY'
}


def load_env(base_dir):
    # Load local .env manually, as python-dotenv needs to be installed into a venv, which not right now.
    print("--- Loading .env to sys env, manually...")
    env_path = base_dir / '.env'
    env_lines = env_path.read_text(encoding='utf-8').splitlines()
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key] = value.strip("'").strip('"')
    
    os.environ['DEBIAN_FRONTEND']='noninteractive'
    os.environ['UBUNTU_FRONTEND']='noninteractive'


def run_command(command, error_message, input=None):
    env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
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
                        if "(Reading database" not in read and "Selecting previously unselected package" not in read and "Preparing to unpack" not in read and "Unpacking" not in read and "inflating:" not in read:
                            print(read.strip())
                elif fd == process.stderr.fileno():
                    read = process.stderr.readline()
                    if read:
                        stderr_content.append(read.strip())
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
            print("-- E1:", error_message)
            return '\n'.join(stdout_content), '\n'.join(stderr_content)

        return '\n'.join(stdout_content), '\n'.join(stderr_content)

    except Exception as e:
        print("-- E2:", str(e))
        sys.exit(1)


class Utility():
    def __init__(self, server_mapping) -> None:
        self.server_mapping = server_mapping


    def get_input_variable(self):
        # SERVER hostname variable, use to check and setup server domains, xray configs, acme keys, ddns keys.
        while True:
            print("------------------------------\nSelect a SERVER config pack:")
            for key, value in self.server_mapping.items():
                print(f"{key}: {value}")
            try:
                server_choice = int(input("------------------------------\nSelect a server to continute: "))
                if server_choice in self.server_mapping:
                    print(f"--- SERVER config pack selected: {self.server_mapping[server_choice]}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")

        # Nginx config types, pre configured and easy to conbine and replace.
        while True:
            print("------------------------------\nSelect a Package with NGINX config type:")
            for key, value in package_mapping.items():
                print(f"{key}: {value}")
            try:
                package_choice = int(input("------------------------------\nSelect a package to continute: "))
                if package_choice in package_mapping:
                    print(f"--- Package with NGINX selected: {package_mapping[package_choice]}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")

        # Xray-core configs, pre configured.
        while True:
            print("------------------------------\nSelect XRAY config type:")
            for key, value in xray_mapping.items():
                print(f"{key}: {value}")
            try:
                xray_choice = int(input("------------------------------\nSelect XRAY config type to continute: "))
                if xray_choice in xray_mapping:
                    print(f"--- XRAY config type selected: {xray_mapping[xray_choice]}...")
                    break
                else:
                    print("Invalid choice, try again.")
            except ValueError:
                print("Invalid input: please enter a number.")

        return server_choice, package_choice, xray_choice


    # A confirmation "prompt" for double-checking high-risk actions.
    def prompt_confirmation(self, prompt, default=False):
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


    # To chekc whether WORDS in FILE.
    def check_config_exsits(self, file_path, content):
        try:
            if content in Path(file_path).read_text():
                return True
        except FileNotFoundError:
            return False
        return False


    def get_platform(self):
        try:
            with open('/etc/os-release') as f:
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


class SafetyPractices:
    def __init__(self, server):
        self.server = server
        self.ssh_port = os.getenv('CUSTOM_SSH_PORT')
        self.ssh_pub_key = os.getenv(f'SSH_KEY_{server}')

        self.ssh_path = Path('~/.ssh').expanduser()
        self.authorized_keys = self.ssh_path / 'authorized_keys'
        self.sshd_config = Path('/etc/ssh/sshd_config')

        self.apply_authorized_keys()
        self.apply_sshd_reconfig()
        self.apply_ufw()


    # Double check your key pair, or you may not be able to login via SSH the next time you connect.
    # Writing key into '~/.ssh/authorized_keys'
    def apply_authorized_keys(self):
        with self.authorized_keys.open('a', encoding='utf-8') as f:
            f.write(f"\n{self.ssh_pub_key}\n")

        os.chmod(self.ssh_path, 0o700)
        os.chmod(self.authorized_keys, 0o600)
        

    # As you can see, replace PORT to your own like, and force enable PUBKEY ONLY mode.
    def apply_sshd_reconfig(self):
        sshd_reconfig = {
            'Port 22': f'Port {self.ssh_port}',
            # 'PermitRootLogin': 'PermitRootLogin no',
            'PubkeyAuthentication no': 'PubkeyAuthentication yes',
            'PasswordAuthentication yes': 'PasswordAuthentication no',
        }

        print("--- Reconfiging sshd service...")
        lines = self.sshd_config.read_text().splitlines()

        new_content = []
        for line in lines:
            for old, new in sshd_reconfig.items():
                if old in line:
                    line = new
                    break
            new_content.append(line)

        self.sshd_config.write_text('\n'.join(new_content) + '\n')
        print(f"--- {self.sshd_config} updated.")

        # Here is the double confirmation. 
        # In fact, after restarting sshd, you will still be online. 
        # Generally speaking, the impact will take effect on the new ssh connection.
        confirm = utility.prompt_confirmation("------------------------------\nRestart sshd service now?")
        if confirm:
            run_command(['sudo', 'service', 'sshd', 'restart'], "Failed to restart sshd service")
            print("--- sshd service restarted...")
        else:
            print("--- Skipping for now.")


    # Enable UFW, and adding 80 443, and your new ssh port.
    def apply_ufw(self):
        print("--- Adding ufw rules...")
        ufw_commands = [
            ['sudo', 'apt-get', 'install', '-y', 'ufw'],
            ['sudo', 'ufw', 'allow', '443/tcp'],
            ['sudo', 'ufw', 'allow', '80/tcp'],
            ['sudo', 'ufw', 'allow', f'{self.ssh_port}/tcp'],
            ['sudo', 'ufw', 'allow', '22/tcp']
        ]
        for cmd in ufw_commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")

        print("--- enable ufw.")
        run_command(['sudo', 'ufw', 'enable'], "", input='y\n'.encode())


class InstallSysComponents:
    def __init__(self) -> None:
        pass

    def install_requirements(self):
        print("--- Installing apt environment requirements...")
        # Interrupting the apt-get process may cause corruption of the dpkg database. If necessary, run "sudo dpkg --configure -a" to repair it.
        commands = [
            ['sudo', 'apt-get', 'clean', 'all', '-y'],
            ['sudo', 'apt-get', 'update', '-y'],
            # ['sudo', 'apt-get', 'upgrade', '-y'],
            ['sudo', 'apt-get', 'autoremove', '-y'],
            ['sudo', 'apt-get', 'install', '-y', 'curl', 'vim', 'git', 'python3.11-venv', 'php-fpm', 'php-xml', 'php-mbstring', 'php-gd', 'php-curl', 'php-zip', 'php-mysql', 'unzip', 'nginx', 'mariadb-server', 'libpam-google-authenticator']
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")


    # Well, there are many reasons to create a python venv.
    def create_virtual_env(self, path):
        venv_name = "appvenv"
        venv_path = path / venv_name
        if not venv_path.exists():
            run_command(['sudo', sys.executable, '-m', 'venv', venv_path], "Failed to create virtual environment")
            print(f"--- Python venv created: {venv_path}...")

        # venv_python = venv_path / 'bin' / 'python'
        # run_command(['sudo', venv_python, '-m', 'pip', 'install', 'request', 'python-dotenv'], "Failed to install requirement.txt")
        return venv_path


    def setup_acme_cert(self, domains):
        # Usage: acme.sh + zerossl + cloudflare.
        # Thank them for promoting a free Internet.
        # 'eab_kid' and 'eab_hmac_key' can be obtained from zerossl website.
        eab_kid = os.getenv('EAB_KID')
        eab_hmac_key = os.getenv('EAB_KEY')
        print("--- Installing acme.sh...")
        user_path = os.path.expanduser('~')

        acme_sh = subprocess.check_output(['curl', '-sSL', 'https://get.acme.sh']).decode('utf-8')
        subprocess.run(['sh'], input=acme_sh, text=True)

        commands = [
            [f'{user_path}/.acme.sh/acme.sh', '--upgrade', '--auto-upgrade'],
            [f'{user_path}/.acme.sh/acme.sh', '--set-default-ca', '--server', 'zerossl'],
            [f'{user_path}/.acme.sh/acme.sh', '--register-account', '--server', 'zerossl', '--eab-kid', eab_kid, '--eab-hmac-key', eab_hmac_key],
        ]
        for cmd in commands:
            run_command(cmd, f"Failed to run {' '.join(cmd)}")

        for domain in domains:
        # This could take a while, be patient.
        # Issue certs and install them to their own path for each domain under the server you selected.
            print(f"--- Issuing certificates for {domain}...")
            
            os.environ['CF_Zone_ID'] = os.getenv(f'CF_Zone_ID_{domain}')
            cert_path = Path('/usr/local/nginx/conf/ssl/') / domain
            cert_path.mkdir(parents=True, exist_ok=True)

            commands = [
                [f'{user_path}/.acme.sh/acme.sh', '--issue', '--force', '--dns', 'dns_cf', '-d', domain, '-d', f'*.{domain}'],
                [f'{user_path}/.acme.sh/acme.sh', '--install-cert', '-d', domain, '--key-file', f'{str(cert_path)}/{domain}.key', '--fullchain-file', f'{str(cert_path)}/fullchain.cer'],
            ]
            for cmd in commands:
                run_command(cmd, f"Failed to run {' '.join(cmd)}")


class InstallPackages:
    def __init__(self, package_choice):
        self.wwwroot_path = Path('/home/wwwroot')
        self.wwwroot_path.mkdir(parents=True, exist_ok=True)

        nextcloud_url = 'https://download.nextcloud.com/server/releases/latest.zip'
        wordpress_url = 'https://wordpress.org/latest.zip'

        # the different package combination and nginx config is defined here.
        if package_choice == 1:
            self.install_xray_core()
            self.wget_wwwroot_package('nextcloud', nextcloud_url)
        elif package_choice == 2:
            self.install_xray_core()
            self.wget_wwwroot_package('nextcloud', nextcloud_url)
            self.install_chatgpt_web()
        elif package_choice == 3:
            self.install_xray_core()
            self.wget_wwwroot_package('wordpress', wordpress_url)

        shutil.chown(self.wwwroot_path, user='www-data', group='www-data')
        os.chmod(self.wwwroot_path, 0o755)


    def install_xray_core(self):
        print("--- Installing xray_core...")
        script_url = "https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
        command = [f'bash -c "$(curl -L {script_url})" @ install -u root']
        subprocess.run(command, check=True, text=True, shell=True)


    # this can be used for any package installed using the wget unpack method.
    def wget_wwwroot_package(self, package, url):
        filename = urlparse(url).path.split('/')[-1]
        file_path = self.wwwroot_path / filename
        os.unlink(file_path) if os.path.isfile(file_path) else None  # fail safe

        print(f"--- Downloading {package} {filename}...")
        run_command(['wget', url, '-P', self.wwwroot_path], f"Failed to download {package}")
        print(f"--- Unzipping {package} {filename}...")
        run_command(['unzip', '-n', file_path, '-d', self.wwwroot_path], f"Failed to unzip {package} file")
        # Attention! This will overwrite existing files, otherwise use '-n' instead of '-o'.
        print(f"--- Removing {package} {filename}...")
        os.unlink(file_path)
        
        if package == 'nextcloud':
            print(f"--- Creating nextcloud data dir...")
            nextcloud_data_path = self.wwwroot_path / 'nextcloud' / 'data'
            nextcloud_data_path.mkdir(parents=True, exist_ok=True)


    # Source Repo: https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.
    def install_chatgpt_web(self):
        if not self.install_docker():
            return
        
        image_name = 'yidadaa/chatgpt-next-web'
        openai_api_key = os.getenv('OPENAI_API_KEY')
        passcode = os.getenv('WEBCHAT_PASSCODE')

        print(f"--- Installing docker {image_name}...")
        stdout, _ = run_command(['sudo', 'docker', 'ps', '-q', '--filter', f"ancestor={image_name}"], "")
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


    # Remember to set your key to sys env or .env.
    def install_docker(self):
        gpg_path = '/usr/share/keyrings/docker-archive-keyring.gpg'
        platform = utility.get_platform()
        if platform == 'debian':
            docker_package = 'https://download.docker.com/linux/debian'
        elif platform == 'ubuntu':
            docker_package = 'https://download.docker.com/linux/ubuntu'
        else:
            print("Platform not supported")
            return False

        print(f"--- Installing docker requirements -> {platform}...")
        run_command(['sudo', 'apt-get', 'install', '-y', 'apt-transport-https', 'ca-certificates', 'gnupg', 'lsb-release'], "Failed to install prerequisites.")

        print("--- Installing docker GPG KEY...")
        curl_output = subprocess.check_output(['sudo', 'curl', '-fsSL', f'{docker_package}/gpg'])
        subprocess.run(['sudo', 'gpg', '--dearmor', '-o', gpg_path], input=curl_output, check=True)

        print("--- Adding docker dpkg sources...")
        architecture, _ = run_command(['sudo', 'dpkg', '--print-architecture'],"")
        release, _ = run_command(['sudo', 'lsb_release', '-cs'],"")
        docker_list_content = f"deb [arch={architecture.strip()} signed-by={gpg_path}] {docker_package} {release.strip()} stable"
        Path('/etc/apt/sources.list.d/docker.list').write_text(docker_list_content)

        print("--- Installing docker CE using apt-get...")
        run_command(['sudo', 'apt-get', 'update', '-y'], "Failed to update package index.")
        run_command(['sudo', 'apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io'], "Failed to install Docker Engine.")

        return True


class SetupSSHGithub():
    def __init__(self) -> None:
        github_repos = os.getenv('GITHUB_REPOS')
        self.github_repos = json.loads(github_repos)

        # new key and config will write to this file
        self.key_dir = Path('~/.ssh').expanduser()
        self.key_path = self.key_dir / 'gh_id_rsa'
        self.config_path = self.key_dir / 'config'

        # Checking github via ssh, for git clone private repo.
        # TODO, skip ssh connetcion check if there;s no private repo on the list.
        if self.setup_git_ssh_conn():
            self.ssh_git_clone()
        return


    def ssh_git_clone(self):
        # Continue looping until exiting manually, or an unexpected error occurs. 
        while True:
            print("------------------------------\nGithub repo list: ")
            for index, repo in enumerate(self.github_repos):
                print(f"{index + 1}: {repo['name']}")

            try:
                repo_choice = int(input("------------------------------\nChoose a repo to clone (0 to exit): "))
                if repo_choice == 0:
                    break
                elif 1 <= repo_choice <= len(self.github_repos):
                    repo = self.github_repos[repo_choice -1]
                    name = repo['name']
                    path = repo['path']

                    print(f"--- Processing git clone <{name}>...")
                    _, stderr = run_command(['git', 'clone', f'git@github.com:{path}.git'],"") # Checking git feedback
                    if "already exists" in stderr:
                        print("--- Reop dir already exists, use 'git pull origin master/main' instead.\n")
                        continue
                else:
                    print("Invalid repo id")
            except ValueError:
                print("Invalid input: please enter a number.")


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
                return False
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
        print("--- Checking ssh git@github.com connection")
        _, stderr = run_command(['ssh', '-T', 'git@github.com'],"", input='yes\n')
        if "successfully authenticated" in stderr:
            return True
        else:
            print("SSH connection test failed:", stderr)
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


class UpdateConfig:
    def __init__(self, base_dir, package_choice, xray_choice, server, domains, php_v):
        self.base_dir = base_dir
        self.package_choice = package_choice
        self.xray_choice = xray_choice
        self.server = server
        self.domain = domains[0]
        self.php_v = php_v

        self.enable_bbr()
        self.update_php_config()
        self.create_vimrc()
        self.move_addons()
        self.replace_config()


    def enable_bbr(self):
        config_lines = [
            "net.core.default_qdisc = fq\n",
            "net.ipv4.tcp_congestion_control = bbr\n"
        ]

        stdout = subprocess.check_output(['sudo', 'sysctl', '-p']).decode()
        if all(line in stdout for line in config_lines):
            print("--- BBR is already enabled")
            return
        
        with Path('/etc/sysctl.conf').open('a', encoding='utf-8') as f:
            f.writelines(config_lines)
        run_command(['sudo', 'sysctl', '-p'], "Failed to reload sysctl configuration")
        print("--- BBR enabled and sysctl reloaded")


    def update_php_config(self): # for small vps
        updates = {
            'pm = dynamic': 'pm = ondemand',
            'pm.max_children = ': 'pm.max_children = 4',
            'pm.start_servers = ': 'pm.start_servers = 1',
            'pm.min_spare_servers = ': 'pm.min_spare_servers = 1',
            'pm.max_spare_servers = ': 'pm.max_spare_servers = 2',
            'pm.process_idle_timeout = ':'pm.process_idle_timeout = 10s;',
            'pm.max_requests = ': 'pm.max_requests = 200',

            'memory_limit = ': 'memory_limit = 64M',
            'upload_max_filesize = ': 'upload_max_filesize = 2M',
            'post_max_size = ': 'post_max_size = 8M',
            'max_execution_time = ': 'max_execution_time = 30',
            'max_input_time = ': 'max_input_time = 30',
            'opcache.enable = ': 'opcache.enable = 1',
            'opcache.memory_consumption = ': 'opcache.memory_consumption = 64',
            'opcache.interned_strings_buffer = 8': 'opcache.interned_strings_buffer = 8',
            'opcache.max_accelerated_files = 4000': 'opcache.max_accelerated_files = 4000',
            'opcache.validate_timestamps = 1': 'opcache.validate_timestamps = 1',
            'opcache.revalidate_freq = 2': 'opcache.revalidate_freq = 2',
        }

        config_paths = [
            Path(f'/etc/php/{self.php_v}/fpm/pool.d/www.conf'),
            Path(f'/etc/php/{self.php_v}/fpm/php.ini'),
            Path(f'/etc/php/{self.php_v}/cli/php.ini')
        ]

        print("--- Updating php configs...")
        for config_path in config_paths:
            lines = config_path.read_text().splitlines()

            new_content = []
            for line in lines:
                for old, new in updates.items():
                    if old in line:
                        line = new
                        break
                new_content.append(line)

            config_path.write_text('\n'.join(new_content) + '\n')
            print(f"--- {config_path} updated.")


    def create_vimrc(self):
        vimrc = """
set mouse-=a
set tabstop=4
set shiftwidth=4
set expandtab
syntax on
colorscheme default
au BufRead,BufNewFile *.conf set syntax=sh
"""
        print("--- Creating .vimrc config...")
        vimrc_path = Path('~/.vimrc').expanduser()
        with vimrc_path.open('a', encoding='utf-8') as f:
            f.write(f"\n{vimrc}\n")
        print(f"--- vim config insert into {vimrc_path}.")


    def move_addons(self):
        addon_path = self.base_dir / 'addons'
        target_path = Path('~/addons').expanduser()
        target_env = target_path / '.env'
        shutil.copytree(addon_path, target_path, dirs_exist_ok=True)

        zone_id = os.getenv(f'CF_Zone_ID_{self.domain}') # only MAIN domain is used
        api_key = os.getenv(f'CF_api_key_{self.domain}') # only MAIN domain is used
        
        with target_env.open('w', encoding='utf-8') as f:
            f.write(f'CF_Zone_ID={zone_id}\n')
            f.write(f'CF_api_key={api_key}\n')

        shutil.chown(target_path, user='root', group='root')
        os.chmod(target_path, 0o755)
        os.chmod(target_env, 0o600)


    def replace_config(self):
        print("--- Replacing nginx & xray config...")
        self.source_paths = {
            1: {"type":"nginx", "choice":1, "source_path": self.base_dir / 'config'/ 'nginx_nextcloud.conf', 'target_name':'nginx.conf'},
            2: {"type":"nginx", "choice":2, "source_path": self.base_dir / 'config'/ 'nginx_nextcloud_chatgpt.conf', 'target_name':'nginx.conf'},
            3: {"type":"nginx", "choice":3, "source_path": self.base_dir / 'config'/ 'location_config.conf', 'target_name':'location_config.conf'},
            4: {"type":"nginx", "choice":3, "source_path": self.base_dir / 'config'/ 'nginx_multi_locations.conf', 'target_name':'nginx.conf'},
            5: {"type":"xray", "choice":1, "source_path": self.base_dir / 'config'/ 'xray_xtls.json', 'target_name':'config.json'},
            6: {"type":"xray", "choice":2, "source_path": self.base_dir / 'config'/ 'xray_reality.json', 'target_name':'config.json'},
        }
        nginx_target_path = Path('/etc/nginx/')
        xray_target_path = Path('/usr/local/etc/xray/')

        self.update_config("nginx", self.package_choice, nginx_target_path)
        self.update_config("xray", self.xray_choice, xray_target_path)


    def update_config(self, type, choice, target_path):
        selected_config = [config for config in self.source_paths.values() if config["type"] == type and config["choice"] == choice]
        for config in selected_config:
            source_path = config["source_path"]
            target_name = config["target_name"]
            target_file = target_path / target_name

            if not target_file.exists():
                print(f"{target_file} does not exists")
                continue

            shutil.copy(source_path, target_file)
            print(f"--- {source_path} -> {target_file}")

            print("--- Replacing yourdomainname with real domain name...")
            content = target_file.read_text()
            new_content = content.replace('yourdomainname', self.domain) # only MAIN domain is used
            target_file.write_text(new_content)

            if type == 'xray':
                print("--- Adding clients for Xray json...")
                xray_clients_json = os.getenv('XRAY_CLIENTS')
                xray_clients = json.loads(xray_clients_json)
                server_clients = xray_clients.get(self.server, [])
                # server_clients = json.dumps(server_clients)
                with open(target_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                for i in data['inbounds']:
                    i['settings']['clients'] = server_clients

                with open(target_file, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=4)

                if self.xray_choice == 2:
                    print("--- Adding REALITY configs...")
                    xray_reality_dest = os.getenv('XRAY_REALITY_DEST') 
                    xray_server_name = os.getenv('XRAY_SERVER_NAME') 
                    xray_reality_key = os.getenv('XRAY_REALITY_KEY') 
                    xray_shortids = os.getenv('XRAY_shortIds') 

                    with open(target_file, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    for i in data['inbounds']:
                        settings = i['streamSettings']['realitySettings']
                        settings['dest'] = xray_reality_dest
                        settings['serverNames'] = json.loads(xray_server_name)
                        settings['privateKey'] = xray_reality_key
                        settings['shortIds'] = json.loads(xray_shortids)

                    with open(target_file, 'w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4)


if __name__ == '__main__':
    BASE_DIR = Path(__file__).resolve().parent

    load_env(BASE_DIR)
    server_mapping = os.getenv('SERVER_MAPPING')
    server_mapping = json.loads(server_mapping)
    server_mapping = {int(k): v for k, v in server_mapping.items()}

    domain_mapping = os.getenv('DOMAIN_MAPPING')
    domain_mapping = json.loads(domain_mapping)

    utility = Utility(server_mapping)
    install_comps = InstallSysComponents()

    server_choice, package_choice, xray_choice = utility.get_input_variable()
    server = server_mapping[server_choice]
    domains = domain_mapping.get(server, [])

    print(">>> Secure system environment...")
    SafetyPractices(server)

    print(">>> Starting system dependency installation...")
    install_comps.install_requirements()

    print(">>> Creating python virtual env...")
    install_comps.create_virtual_env(Path('~/').expanduser())

    print(">>> Installing and setup acme.sh...")
    install_comps.setup_acme_cert(domains)

    print(">>> Installing selected packages...")
    InstallPackages(package_choice)

    print(">>> Setup Git@Github SSH Connection")
    SetupSSHGithub()

    # print(">>> Setting up Mysql...")
    # run'sudo mysql_secure_installation' manually

    php_v, _ = run_command(['php', '-v'], "")
    php_v = ".".join(php_v.split()[1].split('.')[:2])

    print(">>> Updating configs...")
    UpdateConfig(BASE_DIR, package_choice, xray_choice, server, domains, php_v)

    print(">>> Restarting services...")
    run_command(['sudo', 'systemctl', 'restart', 'nginx'], "Failed to restart nginx")
    run_command(['sudo', 'systemctl', 'restart', 'xray'], "Failed to restart xray")
    run_command(['sudo', 'systemctl', 'restart', f'php{php_v}-fpm'], "Failed to restart php-fpm")

    print(">>> Deployment completed.")
