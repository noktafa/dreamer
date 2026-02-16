resource "digitalocean_ssh_key" "poc_key" {
  name       = var.ssh_key_name
  public_key = file(var.ssh_public_key_path)
}
