variable "aws_region" {
  description = "AWS region in which to create the state bucket."
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform remote state."
  type        = string
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
