variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-1"
}

variable "project" {
  description = "Project name, used to prefix resource names"
  type        = string
  default     = "forekto"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "forekto"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# A small, cost-conscious node group. Even so, an EKS control plane and nodes
# cost real money — this configuration is written to review and apply on
# demand, not to be left running.
variable "node_instance_types" {
  description = "EC2 instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project   = "forekto"
    ManagedBy = "terraform"
  }
}
