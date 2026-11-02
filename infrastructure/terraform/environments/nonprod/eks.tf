variable "eks_kubernetes_version" {
  description = "EKS minor version; 1.35 was verified in standard support in us-east-1."
  type        = string
  default     = "1.35"
}

variable "eks_admin_principal_arn" {
  description = "Explicit stable IAM ARN of the local provisioning administrator."
  type        = string
}

variable "eks_public_endpoint_enabled" {
  description = "Enable public API access only when trusted CIDRs are configured."
  type        = bool
  default     = false
}

variable "eks_trusted_public_cidrs" {
  description = "Trusted public administrator IPv4 CIDRs, normally a single /32."
  type        = list(string)
  default     = []
}

variable "eks_node_instance_type" {
  description = "On-demand x86_64 worker type."
  type        = string
  default     = "t3.medium"
}

module "eks" {
  source = "../../modules/eks"

  aws_account_id = var.aws_account_id

  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  kubernetes_version      = var.eks_kubernetes_version
  admin_principal_arn     = var.eks_admin_principal_arn
  public_endpoint_enabled = var.eks_public_endpoint_enabled
  trusted_public_cidrs    = var.eks_trusted_public_cidrs
  node_instance_type      = var.eks_node_instance_type

  # Wait for NAT and private routes before managed nodes attempt bootstrap.
  depends_on = [module.networking]
}
