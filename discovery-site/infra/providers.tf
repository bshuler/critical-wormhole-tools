provider "aws" {
  region = "us-east-1"

  # Role assumption is handled via AWS_PROFILE in the Makefile
  # Profile: criticalwormholebrowser-prod

  default_tags {
    tags = {
      Project     = "criticalwormholebrowser"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}
