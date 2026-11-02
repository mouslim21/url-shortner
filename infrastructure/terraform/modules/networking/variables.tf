variable "project" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "url-shortner"
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
  default     = "nonprod"
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "Provide a valid IPv4 VPC CIDR."
  }
}

variable "public_subnet_cidrs" {
  description = "Two public IPv4 subnet CIDRs, in Availability Zone order."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2 && alltrue([for cidr in var.public_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide exactly two valid public IPv4 subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  description = "Two private IPv4 subnet CIDRs, in Availability Zone order."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2 && alltrue([for cidr in var.private_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide exactly two valid private IPv4 subnet CIDRs."
  }
}

variable "availability_zones" {
  description = "Optional pair of available standard AZs; empty selects two automatically."
  type        = list(string)
  default     = []

  validation {
    condition     = length(var.availability_zones) == 0 || (length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2)
    error_message = "Provide either no AZs or exactly two distinct AZs."
  }
}
