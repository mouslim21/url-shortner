variable "existing_oidc_provider_arn" {
  description = "Reuse an existing GitHub OIDC provider instead of creating another one."
  type        = string
  default     = null

  validation {
    condition = var.existing_oidc_provider_arn == null || can(regex(
      "^arn:aws:iam::292681319373:oidc-provider/token\\.actions\\.githubusercontent\\.com$",
      var.existing_oidc_provider_arn
    ))
    error_message = "Use the GitHub OIDC provider ARN from AWS account 292681319373."
  }
}
