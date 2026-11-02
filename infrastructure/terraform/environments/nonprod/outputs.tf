output "github_actions_role_arn" {
  description = "Role ARN to set as the GitHub Actions AWS_ROLE_ARN repository variable."
  value       = module.github_oidc.github_actions_role_arn
}

output "oidc_provider_arn" {
  description = "GitHub OIDC provider ARN."
  value       = module.github_oidc.oidc_provider_arn
}
