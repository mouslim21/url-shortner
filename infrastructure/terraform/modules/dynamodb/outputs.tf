output "short_urls_table_name" {
  description = "Table name for URLS_TABLE_NAME."
  value       = aws_dynamodb_table.application["short_urls"].name
}

output "short_urls_table_arn" {
  description = "URL table ARN for later Pod Identity permissions."
  value       = aws_dynamodb_table.application["short_urls"].arn
}

output "analytics_table_name" {
  description = "Table name for ANALYTICS_TABLE_NAME."
  value       = aws_dynamodb_table.application["url_analytics"].name
}

output "analytics_table_arn" {
  description = "Analytics table ARN for later Pod Identity permissions."
  value       = aws_dynamodb_table.application["url_analytics"].arn
}
