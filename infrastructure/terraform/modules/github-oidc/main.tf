resource "aws_iam_openid_connect_provider" "github" {
  count = var.existing_oidc_provider_arn == null ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # IAM retrieves the certificate thumbprint; no static thumbprint is needed.
}

locals {
  oidc_provider_arn = var.existing_oidc_provider_arn != null ? var.existing_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
}

resource "aws_iam_role" "github_actions" {
  name        = "url-shortner-github-actions"
  description = "GitHub Actions OIDC authentication for mouslim21/url-shortner main."

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = local.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:mouslim21/url-shortner:ref:refs/heads/main"
        }
      }
    }]
  })

}

resource "aws_iam_role_policy" "ecr_push" {
  name   = "url-shortner-ecr-push"
  role   = aws_iam_role.github_actions.id
  policy = file("${path.module}/ecr-push-policy.json")
}
