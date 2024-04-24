
import json
import subprocess

data = subprocess.check_output("conda list --json", shell=True)
packages = json.loads(data)

for package in packages:
    print(f"{package['channel']}::{package['name']}=={package['version']}")