resource "digitalocean_firewall" "poc" {
  name        = "banking-poc-fw"
  droplet_ids = [for d in digitalocean_droplet.droplets : d.id]

  # SSH from anywhere
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTP to LB
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Kibana
  inbound_rule {
    protocol         = "tcp"
    port_range       = "5601"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # RabbitMQ Management
  inbound_rule {
    protocol         = "tcp"
    port_range       = "15672"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # LLM Service API
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # VPC internal TCP
  inbound_rule {
    protocol         = "tcp"
    port_range       = "1-65535"
    source_addresses = [var.vpc_ip_range]
  }

  # VPC internal UDP
  inbound_rule {
    protocol         = "udp"
    port_range       = "1-65535"
    source_addresses = [var.vpc_ip_range]
  }

  # VPC internal ICMP
  inbound_rule {
    protocol         = "icmp"
    source_addresses = [var.vpc_ip_range]
  }

  # Outbound: allow all
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
