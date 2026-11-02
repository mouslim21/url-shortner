variable "cluster_name" {
  description = "Existing EKS cluster name."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes minor version for compatible Pod Identity Agent selection."
  type        = string
}

variable "short_urls_table_arn" {
  description = "Existing short_urls DynamoDB table ARN."
  type        = string
}

variable "analytics_table_arn" {
  description = "Existing url_analytics DynamoDB table ARN."
  type        = string
}
