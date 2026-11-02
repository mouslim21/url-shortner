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
