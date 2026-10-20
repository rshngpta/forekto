terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # For a real deployment, store state remotely (S3 + DynamoDB lock) instead of
  # a local file. Left commented so `terraform init` works with no AWS account.
  # backend "s3" {
  #   bucket         = "forekto-tfstate"
  #   key            = "horse-racing/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "forekto-tf-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}
