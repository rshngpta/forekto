# Container registry for the horse-racing image. The CD pipeline pushes here,
# and EKS pulls from here.
resource "aws_ecr_repository" "horse_racing" {
  name                 = "${var.project}-horse-racing"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# Keep only the 10 most recent images to control storage cost.
resource "aws_ecr_lifecycle_policy" "horse_racing" {
  repository = aws_ecr_repository.horse_racing.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
