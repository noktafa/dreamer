#!/usr/bin/env python3
"""dreamrunner.py — Deploy and tear down the dreamer infrastructure.

Usage:
    python3 dreamrunner.py deploy    # full pipeline
    python3 dreamrunner.py destroy   # teardown
"""

import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

# Paths (relative to this script's location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_DIR = os.path.join(SCRIPT_DIR, "terraform")
ANSIBLE_DIR = os.path.join(SCRIPT_DIR, "ansible")
INVENTORY_DIR = os.path.join(ANSIBLE_DIR, "inventory")
INVENTORY_FILE = os.path.join(INVENTORY_DIR, "hosts.ini")
TFVARS_FILE = os.path.join(TERRAFORM_DIR, "terraform.tfvars")
SITE_PLAYBOOK = os.path.join(ANSIBLE_DIR, "playbooks", "site.yml")


# ── Helpers ──────────────────────────────────────────────────────────


def fatal(msg):
    print(f"\n✗ {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg):
    print(f"→ {msg}")


def header(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def run(cmd, cwd=None, env=None, check=True):
    """Run a command, streaming output live. Returns CompletedProcess."""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, cwd=cwd, env=merged_env)
    if check and result.returncode != 0:
        fatal(f"Command failed (exit {result.returncode}): {' '.join(cmd)}")
    return result


def capture(cmd, cwd=None):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        fatal(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


# ── Prerequisites ────────────────────────────────────────────────────


def check_prerequisites():
    header("Checking prerequisites")
    missing = []
    for tool in ("terraform", "ansible-playbook", "python3"):
        if shutil.which(tool):
            info(f"{tool} — found")
        else:
            missing.append(tool)
    if missing:
        fatal(f"Missing required tools: {', '.join(missing)}\nInstall them and retry.")


# ── Secrets / tfvars ─────────────────────────────────────────────────


def _prompt_token(name, env_var):
    """Prompt for a token, showing masked current value if set in env."""
    current = os.environ.get(env_var, "")
    if current:
        masked = current[:4] + "…" + current[-4:]
        value = input(f"{name} [{masked}]: ").strip()
        if not value:
            value = current
    else:
        value = getpass.getpass(f"{name}: ").strip()
    if not value:
        fatal(f"{name} is required.")
    os.environ[env_var] = value
    return value


def resolve_secrets():
    """Return (do_token, openai_key), always confirming interactively."""
    header("Resolving secrets")

    do_token = _prompt_token("DIGITALOCEAN_TOKEN", "DIGITALOCEAN_TOKEN")
    openai_key = _prompt_token("OPENAI_API_KEY", "OPENAI_API_KEY")

    return do_token, openai_key


def write_tfvars(do_token):
    header("Writing terraform.tfvars")
    content = (
        f'do_token            = "{do_token}"\n'
        f'ssh_public_key_path = "~/.ssh/id_rsa.pub"\n'
        f'region              = "fra1"\n'
    )
    with open(TFVARS_FILE, "w") as f:
        f.write(content)
    info(f"Written to {TFVARS_FILE}")


# ── Terraform ────────────────────────────────────────────────────────


def terraform_init_apply():
    header("Terraform init")
    run(["terraform", "init"], cwd=TERRAFORM_DIR)

    header("Terraform apply")
    run(["terraform", "apply", "-auto-approve"], cwd=TERRAFORM_DIR)


def terraform_outputs():
    """Parse terraform outputs and return (droplet_ips, lb_ip, llm_url, kibana_url, rabbitmq_url)."""
    header("Reading Terraform outputs")

    raw = capture(["terraform", "output", "-json"], cwd=TERRAFORM_DIR)
    outputs = json.loads(raw)

    droplet_ips = outputs["droplet_ips"]["value"]
    lb_ip = outputs["lb_public_ip"]["value"]
    llm_url = outputs["llm_service_url"]["value"]
    kibana_url = outputs["kibana_url"]["value"]
    rabbitmq_url = outputs["rabbitmq_mgmt_url"]["value"]

    info(f"LB IP: {lb_ip}")
    info(f"LLM service: {llm_url}")
    info(f"Kibana: {kibana_url}")
    info(f"RabbitMQ UI: {rabbitmq_url}")

    return droplet_ips, lb_ip, llm_url, kibana_url, rabbitmq_url


# ── Ansible inventory ────────────────────────────────────────────────


def generate_inventory(droplet_ips):
    header("Generating Ansible inventory")

    groups = {
        "lb": ["lb"],
        "app_servers": ["app1", "app2"],
        "rabbitmq": ["rabbitmq"],
        "consumer": ["consumer"],
        "postgresql": ["postgresql"],
        "elk": ["elk"],
    }

    lines = []
    for group_name, keys in groups.items():
        lines.append(f"[{group_name}]")
        for key in keys:
            if key in droplet_ips:
                d = droplet_ips[key]
                lines.append(
                    f"{d['name']} ansible_host={d['public_ip']} private_ip={d['private_ip']}"
                )
        lines.append("")

    lines.append("[nginx:children]")
    lines.append("lb")
    lines.append("app_servers")
    lines.append("")

    lines.append("[all:vars]")
    lines.append("ansible_user=root")
    lines.append("ansible_python_interpreter=/usr/bin/python3")

    os.makedirs(INVENTORY_DIR, exist_ok=True)
    with open(INVENTORY_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")

    info(f"Inventory written to {INVENTORY_FILE}")


# ── Ansible deploy ───────────────────────────────────────────────────


def run_ansible():
    header("Running Ansible site.yml")
    run(
        ["ansible-playbook", SITE_PLAYBOOK, "-i", INVENTORY_FILE],
        cwd=ANSIBLE_DIR,
        env={"OPENAI_API_KEY": os.environ["OPENAI_API_KEY"]},
    )


# ── Health checks ────────────────────────────────────────────────────


def health_check(url, label):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            info(f"{label}: {resp.status} — {body[:200]}")
            return True
    except (urllib.error.URLError, OSError) as e:
        info(f"{label}: FAILED — {e}")
        return False


def run_health_checks(lb_ip, llm_url):
    header("Health checks")
    health_check(f"http://{lb_ip}/api/health", "Load Balancer")
    health_check(f"{llm_url}/api/health", "LLM Service")


# ── Summary ──────────────────────────────────────────────────────────


def print_summary(droplet_ips, lb_ip, llm_url, kibana_url, rabbitmq_url):
    header("Deployment complete")

    print("\nDroplet IPs:")
    for key, d in sorted(droplet_ips.items()):
        print(f"  {key:12s}  public={d['public_ip']:16s}  private={d['private_ip']}")

    print(f"\nService URLs:")
    print(f"  Load Balancer:  http://{lb_ip}")
    print(f"  LLM Service:    {llm_url}")
    print(f"  Kibana:         {kibana_url}")
    print(f"  RabbitMQ UI:    {rabbitmq_url}")

    print(f"\nTo run tests:")
    print(f"  export LB_URL=http://{lb_ip}")
    print(f"  export LLM_URL={llm_url}")
    print(f"  cd tests && python3 -m pytest")


# ── Commands ─────────────────────────────────────────────────────────


def cmd_deploy():
    check_prerequisites()
    do_token, _ = resolve_secrets()
    write_tfvars(do_token)
    terraform_init_apply()
    droplet_ips, lb_ip, llm_url, kibana_url, rabbitmq_url = terraform_outputs()
    generate_inventory(droplet_ips)
    run_ansible()
    run_health_checks(lb_ip, llm_url)
    print_summary(droplet_ips, lb_ip, llm_url, kibana_url, rabbitmq_url)


def cmd_destroy():
    header("Terraform destroy")
    run(["terraform", "destroy", "-auto-approve"], cwd=TERRAFORM_DIR)

    if os.path.exists(INVENTORY_FILE):
        os.remove(INVENTORY_FILE)
        info(f"Removed {INVENTORY_FILE}")

    header("Teardown complete")


# ── Main ─────────────────────────────────────────────────────────────


USAGE = """\
Usage: python3 dreamrunner.py <command>

Commands:
  deploy    Provision infrastructure, configure with Ansible, and run health checks
  destroy   Tear down all infrastructure and clean up generated files
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    command = sys.argv[1]
    if command == "deploy":
        cmd_deploy()
    elif command == "destroy":
        cmd_destroy()
    else:
        print(f"Unknown command: {command}\n")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
