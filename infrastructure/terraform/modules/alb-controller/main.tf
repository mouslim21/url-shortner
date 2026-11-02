locals {
  tags = {
    Project     = "url-shortner"
    Environment = "nonprod"
    ManagedBy   = "Terraform"
  }
}

resource "aws_iam_role" "controller" {
  name = "${var.cluster_name}-alb-controller"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-name"           = var.cluster_name
          "aws:RequestTag/kubernetes-namespace"       = "kube-system"
          "aws:RequestTag/kubernetes-service-account" = "aws-load-balancer-controller"
        }
      }
    }]
  })
  tags = local.tags
}

resource "aws_iam_policy" "controller" {
  name = "${var.cluster_name}-alb-controller"
  # Unmodified official policy for controller v3.6.2, including AWS tag conditions:
  # https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.2/docs/install/iam_policy.json
  policy = file("${path.module}/iam-policy-v3.6.2.json")
  tags   = local.tags
}

resource "aws_iam_role_policy_attachment" "controller" {
  role       = aws_iam_role.controller.name
  policy_arn = aws_iam_policy.controller.arn
}

resource "aws_eks_pod_identity_association" "controller" {
  cluster_name    = var.cluster_name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.controller.arn
  tags            = local.tags

  depends_on = [aws_iam_role_policy_attachment.controller]
}
