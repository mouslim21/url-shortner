variable "cluster_name" {
  type        = string
  description = "Existing EKS cluster name."
}
variable "kubernetes_version" {
  type        = string
  description = "EKS version used for compatible add-on selection."
}
variable "table_names" {
  type        = set(string)
  description = "Existing application tables to monitor."
}
variable "alert_email" {
  type        = string
  description = "Optional SNS email recipient; confirmation is required."
  default     = ""
  validation {
    condition     = var.alert_email == "" || can(regex("^[^@ ]+@[^@ ]+\\.[^@ ]+$", var.alert_email))
    error_message = "Use an email address or leave empty to disable the subscription."
  }
}
variable "alb_arn_suffix" {
  type        = string
  description = "Discovered ALB ARN suffix app/name/id; empty disables ALB alarms."
  default     = ""
  validation {
    condition     = var.alb_arn_suffix == "" || can(regex("^app/[A-Za-z0-9-]+/[0-9a-f]+$", var.alb_arn_suffix))
    error_message = "Supply the actual app/name/id suffix, not an ARN or hostname."
  }
}
variable "target_group_arn_suffix" {
  type        = string
  description = "Discovered frontend target group suffix targetgroup/name/id."
  default     = ""
  validation {
    condition     = var.target_group_arn_suffix == "" || can(regex("^targetgroup/[A-Za-z0-9-]+/[0-9a-f]+$", var.target_group_arn_suffix))
    error_message = "Supply the actual targetgroup/name/id suffix."
  }
}
