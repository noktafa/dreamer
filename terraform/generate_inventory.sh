#!/bin/bash
set -euo pipefail

INVENTORY_DIR="../ansible/inventory"
INVENTORY_FILE="${INVENTORY_DIR}/hosts.ini"

mkdir -p "$INVENTORY_DIR"

echo "Generating Ansible inventory from Terraform outputs..."

terraform output -json droplet_ips | python3 -c "
import json, sys

data = json.load(sys.stdin)

groups = {
    'lb': ['lb'],
    'app_servers': ['app1', 'app2'],
    'rabbitmq': ['rabbitmq'],
    'consumer': ['consumer'],
    'postgresql': ['postgresql'],
    'elk': ['elk'],
}

lines = []
for group_name, keys in groups.items():
    lines.append(f'[{group_name}]')
    for key in keys:
        if key in data:
            d = data[key]
            lines.append(f\"{d['name']} ansible_host={d['public_ip']} private_ip={d['private_ip']}\")
    lines.append('')

lines.append('[nginx:children]')
lines.append('lb')
lines.append('app_servers')
lines.append('')

lines.append('[all:vars]')
lines.append('ansible_user=root')
lines.append('ansible_python_interpreter=/usr/bin/python3')

print('\n'.join(lines))
" > "$INVENTORY_FILE"

echo "Inventory written to $INVENTORY_FILE"
cat "$INVENTORY_FILE"
