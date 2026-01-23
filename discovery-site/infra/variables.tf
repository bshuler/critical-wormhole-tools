variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Custom domain for the discovery site"
  type        = string
  default     = "discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for the domain"
  type        = string
  default     = "Z09710111ZZGP299W8UMI"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for the domain"
  type        = string
  default     = "arn:aws:acm:us-east-1:256140316797:certificate/e15f7a41-b13c-4529-8778-cabfa04c9664"
}

variable "parent_zone_id" {
  description = "Route53 hosted zone ID for the parent zone (criticalwormholebrowser.apps.criticalwormhole.tools)"
  type        = string
  default     = "Z03667952UZ1NQEZBHI4F"
}

locals {
  bucket_name = "criticalwormholebrowser-${var.environment}-discovery-256140316797"
}
