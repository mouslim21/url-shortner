resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count               = local.alb_enabled ? 1 : 0
  alarm_name          = "url-shortner-nonprod-alb-5xx"
  alarm_description   = "ALB-generated plus target HTTP 5xx: at least 5 per minute for two minutes."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 5
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  metric_query {
    id          = "errors"
    expression  = "elb + target"
    label       = "Combined HTTP 5xx"
    return_data = true
  }
  metric_query {
    id = "elb"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_ELB_5XX_Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = var.alb_arn_suffix }
    }
  }
  metric_query {
    id = "target"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      period      = 60
      stat        = "Sum"
      dimensions  = { LoadBalancer = var.alb_arn_suffix }
    }
  }
  tags = local.tags
}
resource "aws_cloudwatch_metric_alarm" "unhealthy" {
  count               = local.alb_enabled ? 1 : 0
  alarm_name          = "url-shortner-nonprod-alb-unhealthy-targets"
  alarm_description   = "At least one registered frontend target unhealthy for two minutes; missing metrics do not detect zero registered targets."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "notBreaching"
  dimensions          = { LoadBalancer = var.alb_arn_suffix, TargetGroup = var.target_group_arn_suffix }
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "throttles" {
  for_each            = var.table_names
  alarm_name          = "url-shortner-nonprod-${each.key}-throttles"
  alarm_description   = "At least one table read/write throttle event in a minute."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  metric_query {
    id          = "throttles"
    expression  = "reads + writes"
    return_data = true
  }
  metric_query {
    id = "reads"
    metric {
      namespace   = "AWS/DynamoDB"
      metric_name = "ReadThrottleEvents"
      period      = 60
      stat        = "Sum"
      dimensions  = { TableName = each.key }
    }
  }
  metric_query {
    id = "writes"
    metric {
      namespace   = "AWS/DynamoDB"
      metric_name = "WriteThrottleEvents"
      period      = 60
      stat        = "Sum"
      dimensions  = { TableName = each.key }
    }
  }
  tags = local.tags
}
