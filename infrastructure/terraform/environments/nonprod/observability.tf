variable "alert_email" {
  type        = string
  default     = ""
  description = "Optional SNS email subscriber; leave empty to skip."
}
variable "alb_arn_suffix" {
  type        = string
  default     = ""
  description = "Real controller-created ALB suffix app/name/id, discovered manually."
}
variable "target_group_arn_suffix" {
  type        = string
  default     = ""
  description = "Real frontend target group suffix targetgroup/name/id."
}
module "observability" {
  source                  = "../../modules/observability"
  cluster_name            = module.eks.cluster_name
  kubernetes_version      = var.eks_kubernetes_version
  table_names             = [module.dynamodb.short_urls_table_name, module.dynamodb.analytics_table_name]
  alert_email             = var.alert_email
  alb_arn_suffix          = var.alb_arn_suffix
  target_group_arn_suffix = var.target_group_arn_suffix
  depends_on              = [module.pod_identity]
}
output "sns_topic_arn" {
  value = module.observability.sns_topic_arn
}
output "cloudwatch_alarm_names" {
  value = module.observability.alarm_names
}
output "container_log_group_names" {
  value = module.observability.log_group_names
}
