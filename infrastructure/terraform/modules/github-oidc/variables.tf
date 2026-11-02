variable "existing_oidc_provider_arn" {
  description = "Reuse an existing GitHub OIDC provider instead of creating another one."
  type        = string
  default     = null

  validation {
    condition = var.existing_oidc_provider_arn == null || can(regex(
      "^arn:aws:iam::${var.aws_account_id}:oidc-provider/token\\.actions\\.githubusercontent\\.com$",
      var.existing_oidc_provider_arn
    ))
    error_message = "Use the GitHub OIDC provider ARN from AWS account ${var.aws_account_id}."
  }
}

variable "aws_account_id" {
  description = "Expected AWS account for IAM principal validation."
  type        = string
  default     = "957280466878"
}

variable "aws_region" {
  description = "Region containing the three image repositories."
  type        = string
  default     = "us-east-1"
}
