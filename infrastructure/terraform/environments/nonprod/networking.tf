variable "networking" {
  description = "Optional network overrides; defaults provide the two-AZ KATA layout."
  type = object({
    vpc_cidr             = optional(string, "10.0.0.0/16")
    public_subnet_cidrs  = optional(list(string), ["10.0.1.0/24", "10.0.2.0/24"])
    private_subnet_cidrs = optional(list(string), ["10.0.11.0/24", "10.0.12.0/24"])
    availability_zones   = optional(list(string), [])
  })
  default = {}
}

module "networking" {
  source = "../../modules/networking"

  project              = "url-shortner"
  environment          = "nonprod"
  vpc_cidr             = var.networking.vpc_cidr
  public_subnet_cidrs  = var.networking.public_subnet_cidrs
  private_subnet_cidrs = var.networking.private_subnet_cidrs
  availability_zones   = var.networking.availability_zones
}
