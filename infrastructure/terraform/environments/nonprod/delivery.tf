module "alb_controller" {
  source = "../../modules/alb-controller"

  cluster_name = module.eks.cluster_name
  # Reuse the existing agent; the controller itself is manually Helm-managed.
  depends_on = [module.pod_identity]
}

module "eks_deployment_access" {
  source = "../../modules/eks-deployment-access"

  cluster_name             = module.eks.cluster_name
  cluster_arn              = module.eks.cluster_arn
  github_oidc_provider_arn = module.github_oidc.oidc_provider_arn
}

output "alb_controller_role_arn" {
  description = "Controller Pod Identity role ARN."
  value       = module.alb_controller.role_arn
}

output "alb_controller_association_id" {
  description = "Controller Pod Identity association ID."
  value       = module.alb_controller.association_id
}

output "github_deployment_role_arn" {
  description = "Set as AWS_DEPLOY_ROLE_ARN in GitHub environment nonprod."
  value       = module.eks_deployment_access.role_arn
}
