variable "aws_region" {
  description = "AWS region for nonprod resources."
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
}

variable "aws_account_id" {
  description = "Expected sandbox account; prevents using credentials for a different account."
  type        = string
  default     = "957280466878"

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "AWS account ID must contain twelve digits."
  }
}
