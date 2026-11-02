terraform {
  # New sandbox: never reuse the old account's bootstrap state.
  backend "local" {
    path = "terraform-957280466878.tfstate"
  }

  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
