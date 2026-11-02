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
