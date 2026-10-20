data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

# --- Network: VPC with public + private subnets across two AZs --------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.project}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  # /20 private + /24 public subnets, one per AZ.
  private_subnets = ["10.0.0.0/20", "10.0.16.0/20"]
  public_subnets  = ["10.0.32.0/24", "10.0.33.0/24"]

  # Worker nodes sit in private subnets and reach the internet via one NAT
  # gateway (single NAT keeps cost down vs one-per-AZ).
  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true

  # Tags EKS needs to discover subnets for load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = var.tags
}

# --- EKS cluster + managed node group --------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.8"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  cluster_endpoint_public_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      desired_size   = var.node_desired_size
      min_size       = var.node_min_size
      max_size       = var.node_max_size
    }
  }

  # Lets the identity running `terraform apply` administer the cluster.
  enable_cluster_creator_admin_permissions = true

  tags = var.tags
}
