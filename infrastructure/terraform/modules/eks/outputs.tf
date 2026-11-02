output "cluster_name" {
  description = "EKS cluster name for kubeconfig and future integrations."
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint."
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64-encoded Kubernetes API CA certificate."
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "node_group_name" {
  description = "Managed node group name."
  value       = aws_eks_node_group.main.node_group_name
}

output "cluster_security_group_id" {
  description = "EKS-managed security group for the control plane and managed nodes."
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "cluster_arn" {
  description = "Cluster ARN for future scoped permissions."
  value       = aws_eks_cluster.main.arn
}

output "cluster_oidc_issuer_url" {
  description = "Cluster issuer URL; this does not create an IAM OIDC provider."
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "node_role_arn" {
  description = "Infrastructure node IAM role ARN; no application DynamoDB permissions."
  value       = aws_iam_role.nodes.arn
}
