# Session State — Cloud-Native Deployment Pipeline

**Date:** 2026-02-16
**Status: Steps 1-4 COMPLETED. Step 5 (Tests) REMAINING.**

## What Was Accomplished

The entire infrastructure is deployed and running in DigitalOcean (fra1 region).

### Steps Completed

1. **Step 1 (Fix Hardcoded Windows Paths)** — Done in prior session
2. **Step 2 (Create Ops Droplet)** — Done in prior session
3. **Step 3 (Bootstrap Ops Droplet)** — Done in prior session
4. **Step 4 (Run Pipeline)** — **Completed this session**
   - `terraform apply` created 7 droplets + VPC + firewall
   - `generate_inventory.sh` wrote Ansible inventory
   - `ansible-playbook site.yml` configured ALL 7 servers (0 failures)

### Issues Fixed This Session

| Issue | Fix |
|-------|-----|
| RabbitMQ Cloudsmith repos had GPG key errors | Rewrote role to use Ubuntu distro `rabbitmq-server` package + cleanup leftover repos |
| `appuser` system account never created | Added to `common` role — needed by app_server, consumer, llm_service |
| Missing log directories `/var/log/app/`, `/var/log/consumer/`, `/var/log/llm_service/` | Added directory creation tasks to each role |
| Filebeat missing `gnupg` prerequisite on non-ELK hosts | Added prerequisite install step |
| Elasticsearch 8.x security auto-config conflicts | Disabled TLS explicitly, reset keystore, fixed data/log directory permissions |
| PostgreSQL missing `python3-psycopg2` (fixed in prior session) | Added to apt install list |

## Infrastructure

### Ops Droplet (Ansible/Terraform controller)
- **IP:** `157.230.24.173`
- **SSH:** `ssh root@157.230.24.173`
- **Project dir:** `/root/dreamer/`
- **SSH key on ops droplet:** `/root/.ssh/id_rsa` (used to reach all app droplets)

### App Droplets

| Role | Hostname | Public IP | Private IP | Size |
|------|----------|-----------|------------|------|
| Load Balancer | poc-lb | 142.93.173.99 | 10.10.0.3 | s-1vcpu-1gb |
| App Server 1 | poc-app1 | 206.81.19.234 | 10.10.0.2 | s-1vcpu-2gb |
| App Server 2 | poc-app2 | 139.59.215.132 | 10.10.0.4 | s-1vcpu-2gb |
| RabbitMQ | poc-rabbitmq | 134.122.89.48 | 10.10.0.6 | s-2vcpu-4gb |
| Consumer | poc-consumer | 159.89.11.59 | 10.10.0.5 | s-1vcpu-2gb |
| PostgreSQL | poc-postgresql | 207.154.215.133 | 10.10.0.7 | s-2vcpu-4gb |
| ELK + LLM | poc-elk | 138.197.191.107 | 10.10.0.8 | s-4vcpu-8gb |

### Verified Working
- `curl http://142.93.173.99/api/health` → `{"status":"healthy","server":"poc-app2"}`
- All Ansible plays completed with 0 failures across all 7 hosts

## What Remains: Step 5 — Run Tests

From the ops droplet:
```bash
ssh root@157.230.24.173

cd /root/dreamer/tests
pip install -r requirements.txt

export LB_URL="http://142.93.173.99"
export LLM_URL="http://138.197.191.107:8080"

python3 load_test.py
python3 simulate_errors.py
python3 demo_analysis.py
```

### Test Prerequisites
- `OPENAI_API_KEY` environment variable must be set on the ops droplet for `demo_analysis.py` (LLM queries)
- The LLM service on poc-elk:8080 needs a valid OpenAI API key to function

## Continuing from macOS

1. Copy the SSH private key from the Windows machine (`C:\Users\Administrator\.ssh\id_rsa`) to your macOS machine (`~/.ssh/id_rsa_ops`)
2. SSH to the ops droplet: `ssh -i ~/.ssh/id_rsa_ops root@157.230.24.173`
3. All tools (terraform, ansible) are already installed on the ops droplet
4. Project is at `/root/dreamer/` on the ops droplet

Alternatively, if the Windows machine's SSH key is already in your macOS SSH agent or `~/.ssh/`, you can connect directly.

## DigitalOcean API Token

The DO API token is stored in:
- `/root/dreamer/terraform/terraform.tfvars` on the ops droplet
- `dreamer/terraform/terraform.tfvars` in the local repo

## Architecture

```
Internet → poc-lb (Nginx LB) → poc-app1/poc-app2 (FastAPI + Nginx)
                                    ↓
                              poc-rabbitmq (RabbitMQ)
                                    ↓
                              poc-consumer (Queue Consumer)
                                    ↓
                              poc-postgresql (PostgreSQL 16)

All servers → Filebeat → poc-elk (Elasticsearch + Logstash + Kibana)
                              ↑
                         LLM Service (FastAPI + OpenAI, port 8080)
```
