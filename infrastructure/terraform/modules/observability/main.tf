locals {
  tags = { Project = "url-shortner", Environment = "nonprod", ManagedBy = "Terraform" }
  log_groups = { for kind in ["application", "dataplane", "host", "performance"] :
    kind => "/aws/containerinsights/${var.cluster_name}/${kind}"
  }
  alb_enabled = var.alb_arn_suffix != "" && var.target_group_arn_suffix != ""
}

data "aws_region" "current" {}
data "aws_eks_addon_version" "observability" {
  addon_name         = "amazon-cloudwatch-observability"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}
data "aws_eks_addon_version" "metrics_server" {
  addon_name         = "metrics-server"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}
resource "aws_cloudwatch_log_group" "container" {
  for_each          = local.log_groups
  name              = each.value
  retention_in_days = 7
  tags              = local.tags
}
resource "aws_iam_role" "collector" {
  name = "${var.cluster_name}-observability"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Condition = { StringEquals = {
        "aws:RequestTag/eks-cluster-name"           = var.cluster_name
        "aws:RequestTag/kubernetes-namespace"       = "amazon-cloudwatch"
        "aws:RequestTag/kubernetes-service-account" = "cloudwatch-agent"
      } }
    }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy" "collector" {
  name = "container-insights-logs-and-metrics"
  role = aws_iam_role.collector.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogStreams", "logs:PutLogEvents"]
        Resource = flatten([for group in aws_cloudwatch_log_group.container : [group.arn, "${group.arn}:*"]])
      },
      {
        Effect    = "Allow", Action = "cloudwatch:PutMetricData", Resource = "*"
        Condition = { StringEquals = { "cloudwatch:namespace" = "ContainerInsights" } }
      },
      {
        Effect    = "Allow"
        Action    = ["logs:DescribeLogGroups", "ec2:DescribeTags", "ec2:DescribeVolumes"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = data.aws_region.current.region } }
      }
    ]
  })
}
resource "aws_eks_addon" "observability" {
  cluster_name  = var.cluster_name
  addon_name    = "amazon-cloudwatch-observability"
  addon_version = data.aws_eks_addon_version.observability.version
  configuration_values = jsonencode({
    applicationSignals = { enabled = false }
    containerLogs      = { enabled = true }
    agent = { config = jsonencode({
      logs = {
        metrics_collected = { kubernetes = {
          cluster_name                = var.cluster_name
          enhanced_container_insights = true
          metrics_collection_interval = 60
        } }
        force_flush_interval = 5
      }
    }) }
  })
  # The official add-on shares cloudwatch-agent SA with Fluent Bit.
  pod_identity_association {
    service_account = "cloudwatch-agent"
    role_arn        = aws_iam_role.collector.arn
  }
  tags       = local.tags
  depends_on = [aws_iam_role_policy.collector, aws_cloudwatch_log_group.container]
}
resource "aws_eks_addon" "metrics_server" {
  cluster_name  = var.cluster_name
  addon_name    = "metrics-server"
  addon_version = data.aws_eks_addon_version.metrics_server.version
  tags          = local.tags
}
resource "aws_sns_topic" "alerts" {
  name = "url-shortner-nonprod-alerts"
  tags = local.tags
}
resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
