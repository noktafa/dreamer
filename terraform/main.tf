terraform {
  required_version = ">= 1.5.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

resource "digitalocean_vpc" "poc" {
  name     = var.vpc_name
  region   = var.region
  ip_range = var.vpc_ip_range
}

resource "digitalocean_droplet" "droplets" {
  for_each = var.droplets

  name     = each.value.name
  region   = var.region
  size     = each.value.size
  image    = var.image
  vpc_uuid = digitalocean_vpc.poc.id
  ssh_keys = [digitalocean_ssh_key.poc_key.fingerprint]
  tags     = ["banking-poc", each.key]

  user_data = file("${path.module}/cloud-init.yml")

  provisioner "remote-exec" {
    inline = ["cloud-init status --wait > /dev/null 2>&1"]

    connection {
      type        = "ssh"
      user        = "root"
      private_key = file(var.ssh_private_key_path)
      host        = self.ipv4_address
    }
  }
}
