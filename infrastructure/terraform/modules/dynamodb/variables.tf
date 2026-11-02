variable "project" {
  description = "Project tag for the application tables."
  type        = string
  default     = "url-shortner"
}

variable "environment" {
  description = "Environment tag for the application tables."
  type        = string
  default     = "nonprod"
}

variable "point_in_time_recovery_enabled" {
  description = "Enable continuous backups; incurs charges based on table size."
  type        = bool
  default     = true
}
