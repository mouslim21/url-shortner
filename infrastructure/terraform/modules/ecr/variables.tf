variable "project" {
  description = "Project name used as the repository prefix and Project tag."
  type        = string
  default     = "url-shortner"
}

variable "environment" {
  description = "Environment tag for the repositories."
  type        = string
  default     = "nonprod"
}
