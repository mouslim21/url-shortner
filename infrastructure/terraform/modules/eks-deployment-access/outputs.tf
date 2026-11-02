output "role_arn" {
  description = "Role ARN for the nonprod environment AWS_DEPLOY_ROLE_ARN variable."
  value       = aws_iam_role.deployment.arn
}
