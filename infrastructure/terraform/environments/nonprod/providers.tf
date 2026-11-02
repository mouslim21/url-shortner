variable "aws_region" {
  description = "AWS region for nonprod resources."
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  region = var.aws_region
}
