locals {
  workloads = {
    url-service = {
      table_arn = var.short_urls_table_arn
      actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
    }
    analytics-service = {
      table_arn = var.analytics_table_arn
      actions   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
    }
  }
  tags = {
    Project     = "url-shortner"
    Environment = "nonprod"
    ManagedBy   = "Terraform"
  }
}

data "aws_eks_addon_version" "pod_identity" {
  addon_name         = "eks-pod-identity-agent"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

resource "aws_eks_addon" "pod_identity" {
  cluster_name  = var.cluster_name
  addon_name    = "eks-pod-identity-agent"
  addon_version = data.aws_eks_addon_version.pod_identity.version
  tags          = local.tags
}

resource "aws_iam_role" "workload" {
  for_each = local.workloads

  name = "${var.cluster_name}-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-name"           = var.cluster_name
          "aws:RequestTag/kubernetes-namespace"       = "url-shortner"
          "aws:RequestTag/kubernetes-service-account" = each.key
        }
      }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "dynamodb" {
  for_each = local.workloads

  name = "${each.key}-table-access"
  role = aws_iam_role.workload[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = each.value.table_arn
    }]
  })
}

resource "aws_eks_pod_identity_association" "workload" {
  for_each = local.workloads

  cluster_name    = var.cluster_name
  namespace       = "url-shortner"
  service_account = each.key
  role_arn        = aws_iam_role.workload[each.key].arn
  tags            = local.tags

  depends_on = [aws_eks_addon.pod_identity, aws_iam_role_policy.dynamodb]
}
