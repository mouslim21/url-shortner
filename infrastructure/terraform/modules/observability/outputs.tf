output "sns_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic; email requires subscriber confirmation."
}
output "alarm_names" {
  value = concat(
    [for alarm in aws_cloudwatch_metric_alarm.throttles : alarm.alarm_name],
    aws_cloudwatch_metric_alarm.alb_5xx[*].alarm_name,
    aws_cloudwatch_metric_alarm.unhealthy[*].alarm_name
  )
  description = "Enabled alarms; ALB alarms are absent until real suffixes are supplied."
}
output "log_group_names" {
  value       = local.log_groups
  description = "Seven-day Container Insights log groups."
}
