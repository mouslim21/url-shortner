output "workload_role_arns" {
  description = "Pod Identity IAM role ARNs by matching Kubernetes ServiceAccount."
  value       = { for name, role in aws_iam_role.workload : name => role.arn }
}

output "association_ids" {
  description = "Pod Identity association IDs by ServiceAccount."
  value       = { for name, association in aws_eks_pod_identity_association.workload : name => association.association_id }
}

output "agent_addon_version" {
  description = "Selected compatible Pod Identity Agent version."
  value       = aws_eks_addon.pod_identity.addon_version
}
