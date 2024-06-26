## Multi-Server Configuration and Deployment Tool

A Python-based flexibly combinable server quick configuration script designed for:
- Automates the configuration and deployment process for multiple pre-configured servers.
- The one-click deployment script integrates package installation, custom repos installation, multi-domain name support, Nginx pre-configuration, and different types of package settings.


### Features
- Automatically configure the required security settings, including sshkey settings, sshd configuration, ufw configuration, etc.;
- Automatically install required system components, including packages required for apt-get update and installation, and installation configuration of other necessary components;
- Customize the required combination of projects, install wget unzip projects, docker projects, etc.;
- Customize the git clone list, you can choose to clone multiple libraries at once and automatically install the dependencies listed in the project;
- Automatic reconfiguration of common configurations such as nginx, xray-core.
- Detailed function execution result monitoring.
- Support multiple domain name certificate issuance and installation.


### Requirements
tested on Debian 12 and Ubuntu 2204


### Setup Instructions

1. **Fork you own repo**: 
  Fork to your library and make changes as you wish.


2. **Install Dependencies**: 
- First, all the modules used are in Python's standard library, so no venv is needed.
- Script performed `sudo apt update && sudo apt upgrade -y` in the script.
- `Dpkg::Options::="--force-confdef"` and `Dpkg::Options::="--force-confold"` Applied.
- So `git` is the only component you need before running the script.
```
apt install git -y
```


3. **Clone the Repository**: 
  Git clone the repository to server (/root by default).
```
git clone https://github.com/Nonosword/server_env_setup
cd server_env_setup
```

4. **Configuration**: 
- Configure the `.env` file with your server details and any other required environmental variables. 
- Double check that the keys are correct, otherwise the script may be interrupted.
- Recommended to use `env_builder.py` in the addons dir, where the required parameters are presented in a JSON structure for easy reading and understanding. After modifying the necessary parameters, run the file to generate the required .env for the script.

  
```
python3 addons/env_builder.py
```
Or you can vim the .env file and paste variables into it:
```
mv env_example .env
vim .env
```

.env Example:
```
# for server pre-configuration, domains and xray json.
SERVER_MAPPING={"1": "server_1", "2": "server_2", "3": "server_3"}
DOMAIN_MAPPING={"server_1": ["domain_1"], "server_2": ["domain_2", "domain_2_2"], "server_3": ["domain_3"]}

# for xray and xray REALITY
XRAY_CLIENTS={"server_1": [{"id": "uuid", "flow": "xtls-rprx-vision", "level": 0, "email": "email"}], "server_2": [{"id": "uuid", "flow": "xtls-rprx-vision", "level": 0, "email": "email"}], "server_3": [{"id": "uuid", "flow": "xtls-rprx-vision", "level": 0, "email": "email"}]}
XRAY_REALITY_DEST='REALITY TARGET:443'
XRAY_SERVER_NAME=["server1", "server2"]
XRAY_REALITY_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
XRAY_shortIds=["xx", "xxxx"]

# for acme.sh
EAB_KID='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
EAB_KEY='ndt-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

CF_Token="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CF_Account_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CF_Zone_ID_domain_1="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CF_Zone_ID_domain_2="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CF_Zone_ID_domain_2_2="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CF_Zone_ID_domain_3="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# CF_api_key_xxxx only used for MAIN DOMAIN DDNS
CF_api_key_domain_1='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
CF_api_key_domain_2='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
CF_api_key_domain_2_2='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
CF_api_key_domain_3='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# for yidadaa/chatgpt-next-web
OPENAI_API_KEY='sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
WEBCHAT_PASSCODE='WEBCHAT_PASSCODE'

# for custom git clone repos
GITHUB_REPOS=[{"name": "server_env_setup", "path": "Nonosword/server_env_setup"}, {"name": "server_env_setup", "path": "Nonosword/server_env_setup"}, {"name": "server_env_setup", "path": "Nonosword/server_env_setup"}]

# for class SafetyPractices()
SSH_KEY_server_1='ssh-rsa AAAAB'
SSH_KEY_server_2='ssh-rsa AAAAB'
SSH_KEY_server_3='ssh-rsa AAAAB'
CUSTOM_SSH_PORT='2202'
```

5. **Setup Start**: 
```
python3 setup.py
```


### License

This script is released under the MIT License. For more details, see the LICENSE file in the repository.
