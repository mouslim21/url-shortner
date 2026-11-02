locals {
  components = toset(["frontend", "url-service", "analytics-service"])
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_ecr_repository" "application" {
  for_each = local.components

  name                 = "${var.project}-${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.tags, { Name = "${var.project}-${each.key}" })
}

resource "aws_ecr_lifecycle_policy" "application" {
  for_each = aws_ecr_repository.application

  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Retain the most recent 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
