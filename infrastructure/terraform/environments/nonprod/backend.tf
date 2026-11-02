# Initialize only after the bootstrap state bucket has been created.
terraform {
  backend "s3" {
    bucket       = "url-shortner-tfstate-292681319373-us-east-1"
    key          = "nonprod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
