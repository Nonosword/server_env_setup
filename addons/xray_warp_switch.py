import sys
import subprocess
from pathlib import Path

switch = {
    '{"protocol": "freedom", "streamSettings": {"sockopt": {"mark": 51888}}, "settings": {"domainStrategy": "UseIP"}, "tag": "WARP"},' : '// Warp outbound placeholder',
    '{"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"},' : '// Warp rules placeholder'
}

nginx_config = Path('/usr/local/etc/xray/config.json')


def replace_content(warp_on=False):
    lines = nginx_config.read_text(encoding="utf-8").splitlines()
    new_config = []
    for line in lines:
        for on, off in switch.items():
            line = line.replace(off, on) if warp_on else line.replace(on, off)
        new_config.append(line)
    nginx_config.write_text("\n".join(new_config), encoding="utf-8")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python xray_warp_switch.py <on|off>")
        sys.exit(1)

    mode = sys.argv[1]
    print(mode)
    
    if mode == 'on':
        replace_content(True)
        subprocess.run(["sudo", "systemctl", "restart", "xray"], check=True)
        print(f"Xray + Warp mode on.")
    else:
        replace_content(False)
        subprocess.run(["sudo", "systemctl", "restart", "xray"], check=True)
        print(f"Warp proxy off.")

