resource "aws_iam_role" "deployment" {
  name = "url-shortner-github-deploy-nonprod"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          # This repository uses GitHub's immutable owner/repository ID format.
          "token.actions.githubusercontent.com:sub" = "repo:mouslim21@55384360/url-shortner@1442711965:environment:nonprod"
        }
      }
    }]
  })
  tags = {
    Project     = "url-shortner"
    Environment = "nonprod"
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_role_policy" "describe_cluster" {
  name = "describe-nonprod-cluster"
  role = aws_iam_role.deployment.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "eks:DescribeCluster"
      Resource = var.cluster_arn
    }]
  })
}

resource "aws_eks_access_entry" "deployment" {
  cluster_name      = var.cluster_name
  principal_arn     = aws_iam_role.deployment.arn
  type              = "STANDARD"
  kubernetes_groups = ["url-shortner-deployers"]
}
