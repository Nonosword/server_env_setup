import sys
import re
import subprocess

xray_on = """
        listen 8082;
        listen [::]:8082;
        listen 8083 http2;
        listen [::]:8083 http2;
"""

xray_off = """
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
"""

nginx_config_path = "/etc/nginx/nginx.conf"


def replace_content(replacement):
    pattern = re.compile(r'# xray_switch_start.*?# xray_switch_end', re.DOTALL)
    try:
        with open(nginx_config_path, "r+") as file:
            config = file.read()
            new_config = pattern.sub(f"# xray_switch_start{replacement}\n# xray_switch_end", config)
            file.seek(0)
            file.write(new_config)
            file.truncate()
    except Exception as e:
        print(f"Failed to switch Xray: {e}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python switch_xray.py <on|off>")
        sys.exit(1)

    mode = sys.argv[1]
    print(mode)
    
    if mode == 'on':
        replace_content(xray_on)
        subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "xray"], check=True)
        print(f"Xray + Nginx mode on.")
    else:
        replace_content(xray_off)
        subprocess.run(["sudo", "systemctl", "stop", "xray"], check=True)
        subprocess.run(["sudo", "systemctl", "restart", "nginx"], check=True)
        print(f"Nginx Only mode on.")

