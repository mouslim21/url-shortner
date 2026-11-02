variable "dynamodb_pitr_enabled" {
  description = "Enable DynamoDB point-in-time recovery; disable only after reviewing sandbox cost constraints."
  type        = bool
  default     = true
}

module "ecr" {
  source = "../../modules/ecr"

  project     = "url-shortner"
  environment = "nonprod"
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  project                        = "url-shortner"
  environment                    = "nonprod"
  point_in_time_recovery_enabled = var.dynamodb_pitr_enabled
}
