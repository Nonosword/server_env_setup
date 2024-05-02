## Personal Multi-Server Configuration and Deployment Script

A portable Python-based script designed for:
Automates the configuration and deployment process for multiple pre-configured servers.
The one-click deployment script integrates package installation, custom repos installation, multi-domain name support, Nginx pre-configuration, and different types of Xray settings.
### Features

- **Multiple Server pre-Configuration**: 
  Pre-configured hostname, domain, json clients for Nginx and Xray.
- **Multiple Domains**: 
  Supports Multiple Domain names on each server.
- **Multiple Package + Nginx Configuration**: 
  Automatically set up different package combinations with appropriate Nginx configuration.
- **Multiple Xray Config type**: 
  Pre-configured Xray json types (XTLS and REALITY) and use server variables for auto-configuration.

### Requirements
tested on Debian 12 and Ubuntu 2204


### Setup Instructions

1. **Fork you own repo**: 
  Fork to your github and make changes as you wish.

2. **Clone the Repository**: 
  Git clone the repository to server (/root by default).
```
git clone https://github.com/Nonosword/server_env_setup
cd server_env_setup
```

3. **Install Dependencies**: 
- First, all the modules used are in Python's standard library, so no venv is needed.
- However, if you have just build the server, this is an absolutely necessary step. 
- Although I also performed `sudo apt update && sudo apt upgrade -y` in the script, but unfortunately, if the package configuration GUI shows up during the `apt upgrade -y` process, the script will freeze.
- I haven't found a solution yet.

```
sudo apt update && sudo apt upgrade -y
```

4. **Configuration**: 
```
mv env_example .env
vim .env
```

Configure the `.env` file with your server details and any other required environmental variables. 
Double check that the keys are correct, otherwise the script may be interrupted.

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
