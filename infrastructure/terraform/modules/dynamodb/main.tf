locals {
  table_names = toset(["short_urls", "url_analytics"])
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_dynamodb_table" "application" {
  for_each = local.table_names

  name         = each.key
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "code"

  attribute {
    name = "code"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.point_in_time_recovery_enabled
  }

  tags = merge(local.tags, { Name = each.key })
}
