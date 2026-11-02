module "pod_identity" {
  source = "../../modules/pod-identity"

  cluster_name         = module.eks.cluster_name
  kubernetes_version   = var.eks_kubernetes_version
  short_urls_table_arn = module.dynamodb.short_urls_table_arn
  analytics_table_arn  = module.dynamodb.analytics_table_arn

  # The agent needs running nodes; WorkerNodePolicy already grants EKS Auth access.
  depends_on = [module.eks]
}

output "workload_role_arns" {
  description = "Application Pod Identity role ARNs by ServiceAccount."
  value       = module.pod_identity.workload_role_arns
}

output "pod_identity_association_ids" {
  description = "Pod Identity associations for application ServiceAccounts."
  value       = module.pod_identity.association_ids
}

output "pod_identity_agent_version" {
  description = "Compatible EKS Pod Identity Agent add-on version."
  value       = module.pod_identity.agent_addon_version
}
