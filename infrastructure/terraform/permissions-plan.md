# Nonprod AWS permission plan

This document prepares later steps; it does not grant permissions. Account:
`292681319373`. Region: `us-east-1`. Review the exact Terraform resources and
provider API calls before preparing each provisioning policy.

## Separate responsibilities

- Local Terraform uses `AWS_PROFILE=kata-dev` for infrastructure provisioning.
  The sandbox administrator controls that identity's permissions. Do not copy
  its credentials into GitHub or extend the CI role to match the local identity.
- GitHub's `url-shortner-github-actions` role uses OIDC from
  `repo:mouslim21@55384360/url-shortner@1442711965:ref:refs/heads/main`, with audience
  `sts.amazonaws.com`. Do not add a GitHub Environment to its job without reviewing
  the resulting OIDC subject, which differs from the branch subject.
- Step 4C adds only ECR authentication and image-push permissions. It creates no
  repositories and grants no infrastructure provisioning or Kubernetes access.
- The standalone OIDC workflow calls STS GetCallerIdentity. That proves identity,
  not authorization to push images or deploy workloads.

## ECR image publishing

The reviewable policy is `modules/github-oidc/ecr-push-policy.json`.
`ecr:GetAuthorizationToken` requires resource `*`. The other five actions target
only these exact ARNs:

- `arn:aws:ecr:us-east-1:292681319373:repository/url-shortner-frontend`
- `arn:aws:ecr:us-east-1:292681319373:repository/url-shortner-url-service`
- `arn:aws:ecr:us-east-1:292681319373:repository/url-shortner-analytics-service`

No repository creation, deletion, policy administration, or image deletion is
allowed. Image pulling and remote build-cache features may require additional
read actions; add them only if the later workflow needs them. Repositories must
exist before an image can be published. IAM token retrieval alone does not grant
access to other repositories.

## Local Terraform provisioning: candidates for later review

These are action examples and scoping requirements, not an executable or complete
policy. Include the read/refresh/tag APIs actually used by the selected resources.
Constrain to this account, region and planned resource ARNs where supported.
Use request/resource tags for creation and ownership where each API supports
those conditions. Some create and discovery APIs need resource `*`; enumerate
those actions separately with supported conditions, never unrestricted service
permissions or `Action = "*"`. Add replacement/deletion actions only when the
reviewed Terraform operation needs them.

| Area | Candidate API permissions | Scope and restrictions |
| --- | --- | --- |
| Remote state | `s3:ListBucket`, `s3:GetBucketLocation`, `s3:GetObject`, `s3:PutObject`; `s3:DeleteObject` for the lockfile only | Existing state bucket; constrain listing to `nonprod/terraform.tfstate` and `nonprod/terraform.tfstate.tflock`. Object reads/writes use those exact paths. No bucket administration or state-object deletion. |
| VPC/networking | `ec2:CreateVpc`, `ec2:CreateSubnet`, `ec2:CreateRouteTable`, `ec2:AssociateRouteTable`, `ec2:CreateRoute`, `ec2:CreateInternetGateway`, `ec2:AttachInternetGateway`, `ec2:CreateSecurityGroup`, ingress/egress authorization, `ec2:ModifyVpcAttribute`, `ec2:CreateTags`, and explicit describe APIs | Planned VPC, subnet, route, gateway and security-group resources. Restrict `aws:RequestedRegion` where supported. NAT/EIP actions only if the final design includes them. No instance-launch permissions by default. |
| ECR repositories | `ecr:CreateRepository`, `ecr:DescribeRepositories`, `ecr:ListTagsForResource`, `ecr:TagResource`; configuration APIs only for selected settings | The three application repository ARNs. Separate provisioning from GitHub image pushing. |
| DynamoDB | `dynamodb:CreateTable`, `dynamodb:DescribeTable`, `dynamodb:UpdateTable`, `dynamodb:ListTagsOfResource`, `dynamodb:TagResource`; TTL configuration only if selected | Exact `short_urls` and `url_analytics` table ARNs. Provisioning does not need item read/write permissions. Pod runtime permissions will be separate. |
| EKS | `eks:CreateCluster`, `eks:DescribeCluster`, `eks:UpdateClusterConfig`, `eks:UpdateClusterVersion`, `eks:DescribeUpdate`, tagging; explicit node-group/add-on APIs only for chosen resources | Planned cluster, node-group and add-on ARNs. Access-entry and Pod Identity association administration belongs to the local provisioner, not the GitHub deployer. |
| IAM | `iam:CreateRole`, `iam:GetRole`, role tagging, `iam:UpdateAssumeRolePolicy`; explicit inline/managed-policy lifecycle actions required by the selected resources | Only planned project roles/policies. Use a reviewed permissions boundary and restrict policy attachments to approved ARNs. Do not allow arbitrary self-escalation or changes to unrelated identities. |
| Passing roles | `iam:PassRole` | Exact cluster/node/service role ARNs and `iam:PassedToService` for the service that assumes each role, such as EKS or EC2. Never allow passing arbitrary roles. |
| Service-linked roles | `iam:CreateServiceLinkedRole` only if missing and required | Restrict `iam:AWSServiceName` to the exact required AWS service. Check existing roles first. |
| CloudWatch | `logs:CreateLogGroup`, `logs:DescribeLogGroups`, `logs:PutRetentionPolicy`, tagging, `cloudwatch:PutMetricAlarm`, `cloudwatch:DescribeAlarms` | Planned application log-group and alarm ARNs where supported. Log ingestion is a separate runtime permission. No monitoring resources in Step 4C. |
| SNS | `sns:CreateTopic`, `sns:GetTopicAttributes`, `sns:SetTopicAttributes`, tagging, `sns:Subscribe` only for selected notification destinations | Planned topic ARNs; restrict subscription protocols/endpoints where supported. Publishing permissions belong to the actual alert producer. |

Before Step 5, select resource names/tags and cluster settings, map the selected
Terraform resources to exact API permissions, and have the sandbox administrator
review them. Check permissions boundaries and sandbox restrictions as well as
identity policies. Use plan errors or audit evidence to refine specific missing
actions; do not resolve access errors by granting AdministratorAccess.

## Later EKS and Helm deployment access

1. Add `eks:DescribeCluster` to the GitHub role for the exact cluster ARN only.
   This lets the workflow obtain endpoint/CA information; it does not authorize
   Kubernetes API operations. The runner also needs network reachability to the
   cluster endpoint.
2. The local provisioner creates a STANDARD EKS access entry for the GitHub IAM
   role, mapped to a dedicated Kubernetes group. Enable an EKS authentication
   mode supporting access entries when the cluster is provisioned.
3. Pre-create the application namespace, a namespaced Role and its RoleBinding.
   Bind that group only in the application namespace, for example `url-shortner`.
   Do not attach AmazonEKSClusterAdminPolicy or bind cluster-admin.
4. Grant only chart-required Kubernetes resources and verbs. Typical Helm needs
   include get/list/watch/create/update/patch/delete for Deployments, Services,
   ConfigMaps, Ingresses and release Secrets, plus read access to Pods, ReplicaSets
   and Events for rollout checks. Secret access is sensitive; namespace isolation
   matters. Review ServiceAccount or other permissions only when the chart uses
   them. Namespace-wide resource permissions are often necessary for Helm's
   generated release names and upgrades.
5. Keep CRDs, controllers, ClusterRoles, ClusterRoleBindings, namespace creation
   and initial RBAC setup with the infrastructure administrator. Helm must target
   the existing namespace without cluster-wide bootstrap privileges.

No EKS permissions, access entries or Kubernetes RBAC are created in Step 4C.

## References

- [AWS ECR image-push permissions](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Passing IAM roles to AWS services](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)
