variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "url-shortner-nonprod-eks"
}

variable "kubernetes_version" {
  description = "Explicit Kubernetes minor version supported by EKS in the target region."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC containing the cluster and nodes."
  type        = string
}

variable "private_subnet_ids" {
  description = "Two existing private subnets in distinct Availability Zones."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) == 2 && length(distinct(var.private_subnet_ids)) == 2
    error_message = "Provide exactly two distinct private subnet IDs."
  }
}

variable "admin_principal_arn" {
  description = "Explicit stable local provisioning IAM user/role ARN, never an STS session ARN."
  type        = string

  validation {
    condition = can(regex(
      "^arn:aws:iam::292681319373:(user|role)/.+$", var.admin_principal_arn
    )) && var.admin_principal_arn != "arn:aws:iam::292681319373:role/url-shortner-github-actions"
    error_message = "Provide a stable IAM user/role ARN in the sandbox, excluding the GitHub publishing role."
  }
}

variable "public_endpoint_enabled" {
  description = "Opt in to CIDR-restricted public API access for local administration."
  type        = bool
  default     = false
}

variable "trusted_public_cidrs" {
  description = "Explicit trusted IPv4 CIDRs for public API access; prefer your public IP/32."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([for cidr in var.trusted_public_cidrs :
      can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) > 0, false)
    ])
    error_message = "Provide valid IPv4 CIDRs narrower than /0."
  }
}

variable "node_instance_type" {
  description = "On-demand x86_64 node instance type; verify regional offerings and quota."
  type        = string
  default     = "t3.medium"
}

variable "log_retention_days" {
  description = "CloudWatch retention for EKS control plane logs."
  type        = number
  default     = 7
}

variable "project" {
  description = "Project resource tag."
  type        = string
  default     = "url-shortner"
}

variable "environment" {
  description = "Environment resource tag."
  type        = string
  default     = "nonprod"
}
