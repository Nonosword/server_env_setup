import sys
import subprocess
from pathlib import Path

switch = {
    "listen 8082": "listen 443 ssl http2",
    "listen [::]:8082": "listen [::]:443 ssl http2",
    "listen 8083 http2": "# listen 8083 # http2",
    "listen [::]:8083 http2": "# listen [::]:8083 # http2"
}

nginx_config = Path('/etc/nginx/nginx.conf')


def replace_content(xray_on=False):
    lines = nginx_config.read_text(encoding="utf-8").splitlines()
    new_config = []
    for line in lines:
        for on, off in switch.items():
            line = line.replace(off, on) if xray_on else line.replace(on, off)
        new_config.append(line)
    nginx_config.write_text("\n".join(new_config), encoding="utf-8")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python switch_xray.py <on|off>")
        sys.exit(1)

    mode = sys.argv[1]
    print(mode)
    
    if mode == 'on':
        replace_content(True)
        subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "xray"], check=True)
        print(f"Xray + Nginx mode on.")
    else:
        replace_content(False)
        subprocess.run(["sudo", "systemctl", "stop", "xray"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
        print(f"Nginx Only mode on.")

