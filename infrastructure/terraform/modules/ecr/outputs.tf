output "frontend_repository_url" {
  description = "Private repository URL for frontend images."
  value       = aws_ecr_repository.application["frontend"].repository_url
}

output "url_service_repository_url" {
  description = "Private repository URL for URL Service images."
  value       = aws_ecr_repository.application["url-service"].repository_url
}

output "analytics_service_repository_url" {
  description = "Private repository URL for Analytics Service images."
  value       = aws_ecr_repository.application["analytics-service"].repository_url
}

output "repository_arns" {
  description = "Private repository ARNs keyed by application component."
  value       = { for component, repository in aws_ecr_repository.application : component => repository.arn }
}
