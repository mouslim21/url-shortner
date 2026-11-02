variable "existing_github_oidc_provider_arn" {
  description = "Set to an existing GitHub OIDC provider ARN to avoid creating a duplicate."
  type        = string
  default     = null
}

module "github_oidc" {
  source = "../../modules/github-oidc"

  existing_oidc_provider_arn = var.existing_github_oidc_provider_arn
}
