output "github_actions_role_arn" {
  description = "Role ARN to set as the GitHub Actions AWS_ROLE_ARN repository variable."
  value       = module.github_oidc.github_actions_role_arn
}

output "oidc_provider_arn" {
  description = "GitHub OIDC provider ARN."
  value       = module.github_oidc.oidc_provider_arn
}

output "vpc_id" {
  description = "Nonprod VPC ID."
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for future public ALBs."
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs for future EKS workers."
  value       = module.networking.private_subnet_ids
}

output "nat_gateway_id" {
  description = "Shared NAT Gateway ID."
  value       = module.networking.nat_gateway_id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID."
  value       = module.networking.internet_gateway_id
}

output "vpc_cidr_block" {
  description = "Nonprod VPC IPv4 CIDR."
  value       = module.networking.vpc_cidr_block
}

output "frontend_repository_url" {
  description = "Private frontend repository URL."
  value       = module.ecr.frontend_repository_url
}

output "url_service_repository_url" {
  description = "Private URL Service repository URL."
  value       = module.ecr.url_service_repository_url
}

output "analytics_service_repository_url" {
  description = "Private Analytics Service repository URL."
  value       = module.ecr.analytics_service_repository_url
}

output "repository_arns" {
  description = "ECR repository ARNs by component."
  value       = module.ecr.repository_arns
}

output "short_urls_table_name" {
  description = "URLS_TABLE_NAME for the URL Service."
  value       = module.dynamodb.short_urls_table_name
}

output "short_urls_table_arn" {
  description = "URL table ARN for Pod Identity."
  value       = module.dynamodb.short_urls_table_arn
}

output "analytics_table_name" {
  description = "ANALYTICS_TABLE_NAME for Analytics Service."
  value       = module.dynamodb.analytics_table_name
}

output "analytics_table_arn" {
  description = "Analytics table ARN for Pod Identity."
  value       = module.dynamodb.analytics_table_arn
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded Kubernetes API CA certificate."
  value       = module.eks.cluster_certificate_authority_data
}

output "node_group_name" {
  description = "EKS managed node group name."
  value       = module.eks.node_group_name
}

output "cluster_security_group_id" {
  description = "EKS-managed cluster security group ID."
  value       = module.eks.cluster_security_group_id
}

output "cluster_arn" {
  description = "EKS cluster ARN."
  value       = module.eks.cluster_arn
}

output "cluster_oidc_issuer_url" {
  description = "Cluster OIDC issuer URL."
  value       = module.eks.cluster_oidc_issuer_url
}

output "node_role_arn" {
  description = "EKS node infrastructure IAM role ARN."
  value       = module.eks.node_role_arn
}
