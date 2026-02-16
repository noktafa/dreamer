variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "ssh_key_name" {
  description = "SSH key name in DigitalOcean"
  type        = string
  default     = "poc-key"
}

variable "ssh_public_key_path" {
  description = "Local path to SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "fra1"
}

variable "image" {
  description = "Droplet OS image"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "vpc_name" {
  description = "VPC name"
  type        = string
  default     = "banking-poc-vpc"
}

variable "vpc_ip_range" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.10.0.0/16"
}

variable "droplets" {
  description = "Droplet definitions"
  type = map(object({
    name = string
    size = string
  }))
  default = {
    lb         = { name = "poc-lb",         size = "s-1vcpu-1gb" }
    app1       = { name = "poc-app1",       size = "s-1vcpu-2gb" }
    app2       = { name = "poc-app2",       size = "s-1vcpu-2gb" }
    rabbitmq   = { name = "poc-rabbitmq",   size = "s-2vcpu-4gb" }
    consumer   = { name = "poc-consumer",   size = "s-1vcpu-2gb" }
    postgresql = { name = "poc-postgresql", size = "s-2vcpu-4gb" }
    elk        = { name = "poc-elk",        size = "s-4vcpu-8gb" }
  }
}
