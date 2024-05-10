import json
from pathlib import Path


config = {
    # for class SafetyPractices()
    "CUSTOM_SSH_PORT": "2202",

    "SSH_KEY_server_1": "ssh-rsa AAAAB",
    "SSH_KEY_server_2": "ssh-rsa AAAAB",
    "SSH_KEY_server_3": "ssh-rsa AAAAB",


    # for server pre-configuration, domains and xray json.
    "SERVER_MAPPING": [
        {
            "name": "server_1", 
            "domain": ["domain_1"]
        },
        {
            "name": "server_2", 
            "domain": ["domain_2", "domain_2.2"]
        },
        {
            "name": "server_3", 
            "domain": ["domain_3"]
        }
    ],

    # for xray and xray REALITY
    "XRAY_CLIENTS": {
        "server_1": [
            {
                "id": "uuid", 
                "flow": "xtls-rprx-vision", 
                "level": 0, 
                "email": "identifier"
            }
        ],
        "server_2": [
            {
                "id": "uuid", 
                "flow": "xtls-rprx-vision", 
                "level": 0, 
                "email": "identifier"
            }
        ],
        "server_3": [
            {
                "id": "uuid", 
                "flow": "xtls-rprx-vision", 
                "level": 0, 
                "email": "identifier"
            }
        ]
    },

    "XRAY_REALITY_DEST": "REALITY target domain:443",
    "XRAY_SERVER_NAME": [
        "target server1", 
        "target server2"
    ],
    "XRAY_REALITY_KEY": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "XRAY_shortIds": [
        "xx", 
        "xxxx"
    ],


    # for custom git clone repos
    # type ":  type or private
    "GITHUB_REPOS": [
        {
            "name": "server_env_setup", 
            "git_path": "Nonosword/server_env_setup",
            "pkg_path": "/ubuntu/server_env_setup",
            "type": "public"
        }, 
        {
            "name": "server_env_setup", 
            "git_path": "Nonosword/server_env_setup",
            "pkg_path": "/ubuntu/server_env_setup",
            "type": "public"
        }, 
        {
            "name": "server_env_setup", 
            "git_path": "Nonosword/server_env_setup",
            "pkg_path": "/ubuntu/server_env_setup",
            "type": "public"
        }
    ],

    # for acme.sh
    "EAB_KID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "EAB_KEY": "ndt-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",

    "CF_Token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_Account_ID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_Zone_ID_domain_1": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_Zone_ID_domain_2": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_Zone_ID_domain_2_2": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_Zone_ID_domain_3": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",

    # CF_api_key_xxxx only used for MAIN DOMAIN DDNS
    "CF_api_key_domain_1": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_api_key_domain_2": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_api_key_domain_2_2": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "CF_api_key_domain_3": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",


    # for yidadaa/chatgpt-next-web
    "OPENAI_API_KEY": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "WEBCHAT_PASSCODE": "WEBCHAT_PASSCODE"

}


env_path = Path(__file__).parent / '.env'

with open(env_path, 'w') as file:
    for key, value in config.items():
        file.write(f"{key}={json.dumps(value)}\n")