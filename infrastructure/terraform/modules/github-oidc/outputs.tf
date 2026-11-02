output "github_actions_role_arn" {
  description = "Role ARN for the GitHub Actions AWS_ROLE_ARN repository variable."
  value       = aws_iam_role.github_actions.arn
}

output "oidc_provider_arn" {
  description = "ARN of the created or reused GitHub OIDC provider."
  value       = local.oidc_provider_arn
}
