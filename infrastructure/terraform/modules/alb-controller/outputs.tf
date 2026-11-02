output "role_arn" {
  description = "Dedicated AWS Load Balancer Controller Pod Identity role."
  value       = aws_iam_role.controller.arn
}

output "association_id" {
  description = "Controller Pod Identity association for kube-system/aws-load-balancer-controller."
  value       = aws_eks_pod_identity_association.controller.association_id
}
