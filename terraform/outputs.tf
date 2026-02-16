output "droplet_ips" {
  description = "Map of all droplets with public and private IPs"
  value = {
    for key, droplet in digitalocean_droplet.droplets : key => {
      name       = droplet.name
      public_ip  = droplet.ipv4_address
      private_ip = droplet.ipv4_address_private
    }
  }
}

output "lb_public_ip" {
  description = "Load balancer public IP"
  value       = digitalocean_droplet.droplets["lb"].ipv4_address
}

output "kibana_url" {
  description = "Kibana dashboard URL"
  value       = "http://${digitalocean_droplet.droplets["elk"].ipv4_address}:5601"
}

output "rabbitmq_mgmt_url" {
  description = "RabbitMQ management UI URL"
  value       = "http://${digitalocean_droplet.droplets["rabbitmq"].ipv4_address}:15672"
}

output "llm_service_url" {
  description = "LLM RAG service URL"
  value       = "http://${digitalocean_droplet.droplets["elk"].ipv4_address}:8080"
}
