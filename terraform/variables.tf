variable "cloud_id" {
  type        = string
  description = "Идентификатор существующего облака Yandex Cloud."
}

variable "folder_id" {
  type        = string
  description = "Идентификатор каталога для стенда."
}

variable "zone" {
  type    = string
  default = "ru-central1-a"
}

variable "name_prefix" {
  type    = string
  default = "otus-dz03"
}

variable "subnet_cidr" {
  type    = string
  default = "10.30.0.0/24"
}

variable "admin_cidrs" {
  type        = list(string)
  description = "Публичные IPv4-адреса администратора в формате CIDR для SSH на балансировщик."
  validation {
    condition     = length(var.admin_cidrs) > 0 && alltrue([for cidr in var.admin_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"])
    error_message = "Укажите IPv4 CIDR администратора, обычно /32; SSH для всего интернета запрещён."
  }
}

variable "ssh_public_key_path" {
  type    = string
  default = "../.local/otus_dz03.pub"
}

variable "ssh_user" {
  type    = string
  default = "otus"
}

variable "image_id" {
  type        = string
  default     = null
  description = "Фиксированный ID Ubuntu 24.04. При null используется текущий образ ubuntu-2404-lts."
}

variable "core_fraction" {
  type    = number
  default = 20
}
