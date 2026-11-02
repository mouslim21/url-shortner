# Nonprod EKS operations

Step 6 prepares Terraform only. No cluster, nodes, access entries or log groups
were deployed by the coding agent.

## Configuration and review

Run from the repository root. The S3 backend must already exist.

```bash
export AWS_PROFILE=kata-dev
export AWS_REGION=us-east-1
aws sts get-caller-identity
cp infrastructure/terraform/environments/nonprod/eks.tfvars.example \
   infrastructure/terraform/environments/nonprod/eks.auto.tfvars
```

Review the ignored `eks.auto.tfvars`. The example contains the verified local
principal `arn:aws:iam::292681319373:user/cloud_user`. Confirm this remains your
intended administrator. For assumed-role credentials, resolve the stable IAM
role ARN, including any role path; do not copy an STS session ARN into an access
entry. GitHub's publishing role is explicitly rejected as the administrator.

The default Kubernetes version is 1.35, verified in standard support in us-east-1
on November 2, 2026. Recheck before deployment:

```bash
aws eks describe-cluster-versions --cluster-versions 1.35
aws ec2 describe-instance-type-offerings --location-type availability-zone \
  --filters Name=instance-type,Values=t3.medium
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A
```

Private API access is always enabled. Public API access is disabled by default.
With private-only access, local kubectl requires a network path into the VPC.
For direct local administration, explicitly set the following in your local
`eks.auto.tfvars`, replacing the example address with your actual current public
IPv4 address (not your VM's LAN address):

```hcl
eks_public_endpoint_enabled = true
eks_trusted_public_cidrs    = ["YOUR_PUBLIC_IPV4/32"]
```

An empty CIDR list when public access is enabled, invalid CIDRs, and /0 are
rejected. Update the trusted address through a reviewed Terraform change when
VPN/ISP egress changes. Private worker traffic does not require adding the NAT
Gateway's public IP to this list because the private endpoint remains enabled.

```bash
terraform -chdir=infrastructure/terraform/environments/nonprod init
terraform -chdir=infrastructure/terraform/environments/nonprod validate
terraform -chdir=infrastructure/terraform/environments/nonprod plan -out=eks.tfplan
```

Review all changes: cluster, node group, two IAM roles and four attachments,
control-plane log group, and the administrator access entry/policy association.
Existing networking, ECR, DynamoDB and GitHub permissions should not be replaced.
The local provisioning identity needs the reviewed EKS/IAM/PassRole/CloudWatch
permissions described in `permissions-plan.md`. A successful plan does not prove
create permissions, live capacity or all sandbox policy restrictions.

Only after explicit approval, run manually:

```bash
terraform -chdir=infrastructure/terraform/environments/nonprod apply eks.tfplan
```

Never reuse an applied plan; generate a fresh plan after state changes.

## Verify after deployment

Use the configured administrator and its AWS profile:

```bash
export AWS_PROFILE=kata-dev
export AWS_REGION=us-east-1
CLUSTER_NAME=$(terraform -chdir=infrastructure/terraform/environments/nonprod output -raw cluster_name)
NODE_GROUP_NAME=$(terraform -chdir=infrastructure/terraform/environments/nonprod output -raw node_group_name)

aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.{Status:status,Version:version,Endpoint:endpoint,Networking:resourcesVpcConfig}'
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODE_GROUP_NAME" \
  --query 'nodegroup.{Status:status,Health:health,Scaling:scalingConfig,Subnets:subnets}'
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region us-east-1 --alias "$CLUSTER_NAME"
kubectl cluster-info
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pods -A
kubectl get namespaces
kubectl auth can-i get nodes
kubectl auth can-i create deployments -n default
```

Expect cluster and node group `ACTIVE`, two `Ready` AL2023 nodes with private
addresses, and nodes distributed across the two selected AZs. Managed node groups
use ASG AZ balancing; actual distribution depends on capacity and must be checked.
CoreDNS, kube-proxy and VPC CNI should be healthy in kube-system. Default/system
namespaces are expected; application workloads are intentionally absent. The two
administrator authorization checks should return `yes`.

## Troubleshooting

- **AWS AccessDenied:** compare `aws sts get-caller-identity` with the configured
  stable administrator ARN. The local identity needs `eks:DescribeCluster` for
  kubeconfig, and Terraform needs provisioning permissions. Do not solve this by
  granting the GitHub publishing role cluster-admin.
- **Kubernetes Unauthorized/Forbidden:** verify the access entry and its
  AmazonEKSClusterAdminPolicy association. Ensure kubectl uses the intended
  context/profile and a current AWS CLI token. AWS IAM permissions and Kubernetes
  access are separate checks.
- **API timeout/CIDR restriction:** verify public endpoint opt-in and your actual
  current public egress /32, or use a host with VPC connectivity for private-only
  access. Check DNS and HTTPS reachability before changing RBAC.
- **Nodes NotReady:** inspect `kubectl describe node` and kube-system pods/events.
  Check VPC CNI permissions, subnet free IPs, VPC DNS, cluster-managed security
  groups and outbound connectivity. Do not open SSH or public node ports.
- **Node-group creation failure:** inspect `aws eks describe-nodegroup` health
  issues. Check IAM role attachments, PassRole/service-linked-role permissions,
  AL2023/x86_64 instance compatibility, EC2 quotas, capacity in both AZs, and
  private subnet routing. Terraform plan cannot guarantee service availability.
- **Missing NAT/outbound connectivity:** verify private default routes point to
  the existing available NAT, that NAT is in a public subnet, and the public
  default route reaches the Internet Gateway. Nodes need outbound HTTPS to ECR,
  S3 and AWS service endpoints; no VPC endpoints are added in this KATA.

## Cost and reliability

EKS control-plane charges apply while the cluster exists; two on-demand
`t3.medium` nodes, their EBS root volumes, control-plane logs and the existing
NAT/public IPv4 also incur charges. Monitor sandbox expiry and review current AWS
pricing before deployment. No exact price estimate is assumed here.

One NAT lowers cost but makes both private subnets' Internet egress depend on one
AZ and can add cross-AZ transfer charges. It does not eliminate private cluster
endpoint access in the other AZ, but outbound-dependent node operations can fail.

The managed node group starts at desired/minimum 2 and maximum 3. These bounds do
not install a node autoscaler. Changing node-group desired size changes EC2 node
capacity. HPA changes application Pod replica counts and does not add EC2 nodes;
HPA also requires metrics and suitable workload requests/configuration. Neither
HPA nor Cluster Autoscaler/Karpenter is installed in Step 6.

Node IAM has worker, ECR pull and IPv4 CNI permissions only, with no DynamoDB
application access. For simplicity, CNI uses the node role during this KATA;
separating CNI identity can be reviewed later. No application Pod Identity
associations, GitHub EKS access, Helm workloads or ALB Controller are included.
