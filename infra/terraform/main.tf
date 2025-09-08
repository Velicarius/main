terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Skeleton only – add ECR, ECS, RDS as needed
output "note" {
  value = "Add ECR/ECS/RDS/IAM configuration here."
}
