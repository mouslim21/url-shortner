locals {
  alb_widgets = local.alb_enabled ? [
    { type = "metric", width = 12, height = 6, properties = {
      title = "ALB requests and HTTP errors", region = data.aws_region.current.region, period = 60, stat = "Sum"
      metrics = [for name in ["RequestCount", "HTTPCode_ELB_5XX_Count", "HTTPCode_Target_5XX_Count"] :
        ["AWS/ApplicationELB", name, "LoadBalancer", var.alb_arn_suffix]
      ]
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title   = "ALB p95 target response seconds", region = data.aws_region.current.region, period = 60, stat = "p95"
      metrics = [["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix]]
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title = "Frontend target health", region = data.aws_region.current.region, period = 60, stat = "Minimum"
      metrics = [for name in ["HealthyHostCount", "UnHealthyHostCount"] :
        ["AWS/ApplicationELB", name, "LoadBalancer", var.alb_arn_suffix, "TargetGroup", var.target_group_arn_suffix]
      ]
    } }
  ] : []
}
resource "aws_cloudwatch_dashboard" "sre" {
  dashboard_name = "url-shortner-nonprod-sre"
  dashboard_body = jsonencode({ widgets = concat(local.alb_widgets, [
    { type = "metric", width = 12, height = 6, properties = {
      title = "Node health and reserved capacity", region = data.aws_region.current.region, period = 60, stat = "Average"
      metrics = [for name in ["cluster_failed_node_count", "node_status_condition_ready", "node_cpu_reserved_capacity", "node_memory_reserved_capacity"] :
        ["ContainerInsights", name, "ClusterName", var.cluster_name]
      ]
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title = "DynamoDB system errors by table and operation", region = data.aws_region.current.region, period = 60, stat = "Sum"
      metrics = flatten([for table in var.table_names : [for operation in ["GetItem", "PutItem", "UpdateItem"] :
        { metric = ["AWS/DynamoDB", "SystemErrors", "TableName", table, "Operation", operation] }
      ]])[*].metric
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title = "Container Insights node CPU and memory percent", region = data.aws_region.current.region, period = 60, stat = "Average"
      metrics = [for name in ["node_cpu_utilization", "node_memory_utilization"] :
        ["ContainerInsights", name, "ClusterName", var.cluster_name]
      ]
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title = "Pod restarts and ready status (enhanced Container Insights)", region = data.aws_region.current.region, period = 60, stat = "Maximum"
      metrics = [for name in ["pod_number_of_container_restarts", "pod_status_ready"] :
        ["ContainerInsights", name, "Namespace", "url-shortner", "ClusterName", var.cluster_name]
      ]
    } },
    { type = "metric", width = 12, height = 6, properties = {
      title = "DynamoDB throttling", region = data.aws_region.current.region, period = 60, stat = "Sum"
      metrics = flatten([for table in var.table_names : [for metric in ["ReadThrottleEvents", "WriteThrottleEvents"] :
        { metric = ["AWS/DynamoDB", metric, "TableName", table] }
      ]])[*].metric
    } }
  ]) })
}
