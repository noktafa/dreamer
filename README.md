<p align="center">
  <img src="assets/logo.svg" alt="dreamer" width="600"/>
</p>

<p align="center">
  Banking system monitoring POC with LLM-powered log analysis on DigitalOcean.
</p>

## Architecture

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

## Stack

- **Infrastructure:** Terraform + DigitalOcean
- **Configuration:** Ansible
- **Application:** Python 3.11+ / FastAPI / Pika
- **Message Queue:** RabbitMQ
- **Database:** PostgreSQL 16
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana) + Filebeat
- **AI Analysis:** OpenAI GPT-4o RAG pipeline

## Quick Start

```bash
# 1. Provision infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your DO token
terraform init && terraform apply

# 2. Generate Ansible inventory
chmod +x generate_inventory.sh
./generate_inventory.sh

# 3. Configure all servers
cd ../ansible
export OPENAI_API_KEY="sk-..."
ansible-playbook playbooks/site.yml

# 4. Run tests
cd ../tests
pip install -r requirements.txt
python load_test.py --url http://<LB_IP>
python simulate_errors.py
python demo_analysis.py

# 5. Cleanup
cd ../terraform && terraform destroy
```

## Project Structure

```
dreamer/
├── terraform/          # DigitalOcean infrastructure (7 droplets, VPC, firewall)
├── ansible/            # Server configuration (12 roles, 3 playbooks)
├── app/                # FastAPI order API (RabbitMQ publisher)
├── consumer/           # RabbitMQ consumer (PostgreSQL writer)
├── llm_service/        # LLM RAG service (Elasticsearch + OpenAI)
├── tests/              # Load test, error simulation, LLM demo
└── docs/               # Phase documentation
```

## API Endpoints

### App Server (port 80 via LB)
- `POST /api/orders` - Submit a banking order
- `GET /api/orders/{correlation_id}` - Query order status
- `GET /api/health` - Health check
- `POST /api/simulate/error` - Trigger simulated errors
- `POST /api/simulate/slow` - Trigger slow responses

### LLM Service (port 8080)
- `POST /api/ask` - Ask questions about system logs
- `GET /api/summary` - Get system health summary
- `GET /api/health` - Health check
