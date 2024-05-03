import os
from pathlib import Path

from src.utility import run_command


class SafetyPractices:
    def __init__(self, server, utility):
        print("->> Initializing security settings...")
        self.utility = utility

        self.ssh_port = os.getenv('CUSTOM_SSH_PORT')
        self.ssh_pub_key = os.getenv(f'SSH_KEY_{server}')

        self.ssh_path = Path('~/.ssh').expanduser()
        self.authorized_keys = self.ssh_path / 'authorized_keys'
        self.sshd_config = Path('/etc/ssh/sshd_config')


    def start_functions(self):
        results = {
            'authorized_keys': self.apply_authorized_keys(),
            'sshd_config': self.apply_sshd_reconfig(),
            'ufw': self.apply_ufw()
        }
        return results


    # Double check your key pair, or you may not be able to login via SSH the next time you connect.
    # Writing key into '~/.ssh/authorized_keys'
    def apply_authorized_keys(self):
        print("->> Sending ssh pubkey to 'authorized_keys'")

        try:
            with self.authorized_keys.open('a', encoding='utf-8') as f:
                f.write(f"\n{self.ssh_pub_key}\n")

            os.chmod(self.ssh_path, 0o700)
            os.chmod(self.authorized_keys, 0o600)
            return True        
        except Exception as e:
            print(e)
            return False


    # As you can see, replace PORT to your own like, and force enable PUBKEY ONLY mode.
    def apply_sshd_reconfig(self):
        print("->> Reconfiging sshd service...")

        sshd_reconfig = {
            'Port 22': f'Port {self.ssh_port}',
            # 'PermitRootLogin': 'PermitRootLogin no',
            'PubkeyAuthentication no': 'PubkeyAuthentication yes',
            'PasswordAuthentication yes': 'PasswordAuthentication no',
        }

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
        confirm = self.utility.prompt_confirmation("------------------------------\nRestart sshd service now?")
        if confirm:
            success, _, _, = run_command(['sudo', 'service', 'sshd', 'restart'], "Failed to restart sshd service")
            print("--- sshd service restarted...")
            return True if success else False
        else:
            print("--- Skipping for now.")
            return None


    # Enable UFW, and adding 80 443, and your new ssh port.
    def apply_ufw(self):
        print("-->> Adding ufw rules and reloading ufw service...")

        ufw_commands = [
            ['sudo', 'apt-get', 'install', '-y', 'ufw'],
            ['sudo', 'ufw', 'allow', '443/tcp'],
            ['sudo', 'ufw', 'allow', '80/tcp'],
            ['sudo', 'ufw', 'allow', f'{self.ssh_port}/tcp'],
            ['sudo', 'ufw', 'allow', '22/tcp'],
            ['sudo', 'ufw', '--force', 'enable']
        ]
        all_success = True
        for cmd in ufw_commands:
            success, _, _ = run_command(cmd, f"Failed to run {' '.join(cmd)}")
            if not success:
                all_success = False
                continue

        return all_success