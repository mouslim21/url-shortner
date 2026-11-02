variable "cluster_name" {
  description = "Existing EKS cluster name."
  type        = string
}

variable "cluster_arn" {
  description = "Existing EKS cluster ARN for DescribeCluster only."
  type        = string
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN."
  type        = string
}
