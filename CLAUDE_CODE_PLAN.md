# CLAUDE_CODE_PLAN.md — Master Orchestration File

## Project Summary

**Goal:** 7-server Linux infrastructure on DigitalOcean for system monitoring and issue analysis with LLM (OpenAI API). POC only — no HA requirements.

**Stack:** Python 3.11+ / FastAPI / Nginx / RabbitMQ / PostgreSQL / ELK Stack / OpenAI API

**Architecture:**
```
Nginx LB (Server 1)
  ├── App Server A (Server 2) ──┐
  └── App Server B (Server 3) ──┤
                                ▼
                         RabbitMQ (Server 4)
                                ▼
                      Queue Consumer (Server 5)
                                ▼
                       PostgreSQL (Server 6)

ELK + LLM RAG Service (Server 7) ← Filebeat from all servers
```

## Directory Structure

```
dreamer/
├── CLAUDE_CODE_PLAN.md
├── docs/
│   ├── phase-0-terraform.md
│   ├── phase-1-ansible.md
│   ├── phase-2-app.md
│   ├── phase-3-consumer.md
│   ├── phase-4-llm-service.md
│   ├── phase-5-configs.md
│   └── phase-6-tests.md
├── terraform/
├── ansible/
├── app/
├── consumer/
├── llm_service/
├── tests/
└── README.md
```

## Phase Checklist

| Phase | File | What It Produces | Verify |
|-------|------|-------------------|--------|
| 0 | `phase-0-terraform.md` | `terraform/` — all .tf files, cloud-init, inventory script | `terraform validate` |
| 1 | `phase-1-ansible.md` | `ansible/` — all roles, playbooks, group_vars | `ansible-playbook --syntax-check` |
| 2 | `phase-2-app.md` | `app/` — FastAPI app with correlation ID, RMQ publisher | `python -m pytest` |
| 3 | `phase-3-consumer.md` | `consumer/` — RabbitMQ consumer, PG writer | `python -m pytest` |
| 4 | `phase-4-llm-service.md` | `llm_service/` — RAG pipeline with OpenAI | `python -m pytest` |
| 5 | `phase-5-configs.md` | Config templates inside ansible roles | Visual review |
| 6 | `phase-6-tests.md` | `tests/` — load test, error sim, LLM demo | Run after deployment |

## Deployment Sequence

```bash
# 1. Infrastructure
cd terraform && terraform init && terraform apply

# 2. Generate Ansible inventory
./generate_inventory.sh

# 3. Configure all servers
cd ../ansible && ansible-playbook -i inventory/hosts.ini playbooks/site.yml

# 4. Test
cd ../tests && python3 load_test.py && python3 simulate_errors.py && python3 demo_analysis.py

# 5. Cleanup
cd ../terraform && terraform destroy
```

## Shared Constants

```yaml
region: fra1
image: ubuntu-24-04-x64
vpc_cidr: 10.10.0.0/16

droplet_sizes:
  lb: s-1vcpu-1gb
  app1: s-1vcpu-2gb
  app2: s-1vcpu-2gb
  rabbitmq: s-2vcpu-4gb
  consumer: s-1vcpu-2gb
  postgresql: s-2vcpu-4gb
  elk: s-4vcpu-8gb

rabbitmq:
  user: app_user
  pass: ***REMOVED***
  vhost: /banking_poc
  exchange: orders_exchange
  queue: orders_queue
  dlx_exchange: dlx_exchange
  dead_letter_queue: dead_letter_queue
  routing_key: orders

postgresql:
  db: banking_poc
  user: app_user
  pass: ***REMOVED***

openai:
  model: gpt-4o

ports:
  public:
    http: 80
    ssh: 22
    kibana: 5601
    rabbitmq_mgmt: 15672
    llm_api: 8080
  internal:
    app: 8000
    rabbitmq: 5672
    postgresql: 5432
    elasticsearch: 9200
    logstash_beats: 5044
```
