variable "existing_github_oidc_provider_arn" {
  description = "Set to an existing GitHub OIDC provider ARN to avoid creating a duplicate."
  type        = string
  default     = null
}

module "github_oidc" {
  source = "../../modules/github-oidc"

  aws_account_id = var.aws_account_id
  aws_region     = var.aws_region

  existing_oidc_provider_arn = var.existing_github_oidc_provider_arn
}
