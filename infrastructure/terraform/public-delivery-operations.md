# Step 8: public ALB and nonprod delivery

This is a manual approval/runbook. No Terraform apply, controller installation,
Kubernetes changes or application deployment were performed by the coding agent.

## Ownership and prerequisites

Terraform manages controller IAM/Pod Identity prerequisites and a separate GitHub
EKS deployment IAM role/access entry. The cluster administrator manually manages
one controller Helm release using official chart **3.6.2**, controller **v3.6.2**.
Its vendored IAM policy is unmodified from:
https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.2/docs/install/iam_policy.json
The official discovery actions need resource `*`; supported create/manage actions
use the upstream resource/tag conditions. No AdministratorAccess is attached.
Do not additionally manage this release through a Terraform Helm provider.

The application chart owns one Ingress. The controller owns its AWS ALB, target
groups and security groups. No aws_lb, extra VPC/NAT or LoadBalancer Service is
created by these files. The controller discovers the two existing public subnets
using kubernetes.io/role/elb tags, and registers private frontend Pod IPs.
All application Services remain ClusterIP. Only frontend receives public traffic;
Nginx forwards API/redirect requests internally. Analytics has no direct ALB route.

The EKS API remains private. CD needs an isolated, trusted self-hosted Linux x64
runner labeled **nonprod-eks**, with HTTPS/DNS connectivity to the private EKS
endpoint and outbound access to GitHub, AWS STS/EKS and Helm download endpoints.
Provide Git, AWS CLI v2, and a current Actions runner supporting the selected
Node-based actions. The workflow installs pinned kubectl and Helm 3 itself.
No runner instances or networking changes are created in Step 8.

Do not route untrusted PR jobs to this runner or give it an ambient AWS instance
role, static credentials, or an administrator kubeconfig. Use an isolated,
preferably ephemeral runner; labels are scheduling selectors, not a security
boundary. Restrict runner use to trusted main-branch deployment workflows using
runner-group/workflow controls where available. PR checks continue on hosted
runners. Never expose the EKS API to all GitHub-hosted runner IPs or 0.0.0.0/0.

Before merging the CD job, manually create/configure GitHub environment `nonprod`:

- Permit deployments only from branch `main`, with no deployment tags.
- Configure a required reviewer and prevent self-review where your GitHub plan
  supports it. Apply available protection/bypass restrictions deliberately.
- Set environment variable `AWS_DEPLOY_ROLE_ARN` to the Terraform output below.
- Keep publishing's repository variable `AWS_ROLE_ARN` unchanged.
- Do not store AWS access keys. Runner registration credentials are managed
  separately outside this repository.

This repository uses immutable GitHub OIDC subjects. The deployment role trusts
only `repo:mouslim21@55384360/url-shortner@1442711965:environment:nonprod` with
`sts.amazonaws.com` audience. This is the actual equivalent of the older name-only
environment subject. Environment subjects omit the branch, so environment branch
protection and the job's main-push guard are essential. The publishing role keeps
its separate main-branch trust and ECR permissions.

## 1. Review and apply infrastructure prerequisites manually

From the repository root, after prior steps exist:

```bash
export AWS_PROFILE=kata-dev
export AWS_REGION=us-east-1
terraform -chdir=infrastructure/terraform/environments/nonprod init
terraform -chdir=infrastructure/terraform/environments/nonprod validate
terraform -chdir=infrastructure/terraform/environments/nonprod plan -out=delivery.tfplan
```

Review the full plan, then only after approval:

```bash
terraform -chdir=infrastructure/terraform/environments/nonprod apply delivery.tfplan
terraform -chdir=infrastructure/terraform/environments/nonprod output github_deployment_role_arn
terraform -chdir=infrastructure/terraform/environments/nonprod output alb_controller_role_arn
terraform -chdir=infrastructure/terraform/environments/nonprod output alb_controller_association_id

gh variable set AWS_DEPLOY_ROLE_ARN --repo mouslim21/url-shortner --env nonprod \
  --body "$(terraform -chdir=infrastructure/terraform/environments/nonprod output -raw github_deployment_role_arn)"
```

The deployment role has only `eks:DescribeCluster` on this cluster ARN. EKS maps
it to Kubernetes group `url-shortner-deployers`; the namespaced RoleBinding below
provides actual Kubernetes permissions. No EKS administrator access policy, ECR
push permissions or DynamoDB data permissions are attached to this role.

## 2. Bootstrap namespace RBAC and the controller as administrator

Use the configured cluster administrator and a host with private connectivity:

```bash
aws eks update-kubeconfig --name url-shortner-nonprod-eks --region us-east-1
kubectl apply -f infrastructure/kubernetes/nonprod-deployer-rbac.yaml
kubectl -n kube-system rollout status daemonset/eks-pod-identity-agent --timeout=180s
aws eks list-pod-identity-associations --cluster-name url-shortner-nonprod-eks

helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
VPC_ID=$(terraform -chdir=infrastructure/terraform/environments/nonprod output -raw vpc_id)
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.6.2 --namespace kube-system \
  -f infrastructure/kubernetes/aws-load-balancer-controller-values.yaml \
  --set-string vpcId="$VPC_ID" --atomic --wait --timeout 10m
kubectl -n kube-system rollout status deployment/aws-load-balancer-controller --timeout=180s
kubectl -n kube-system get serviceaccount aws-load-balancer-controller
kubectl -n kube-system logs deployment/aws-load-balancer-controller --tail=100
kubectl get ingressclass alb
```

The chart creates its own ServiceAccount, RBAC, webhook and necessary CRDs.
Terraform's association already matches kube-system/aws-load-balancer-controller.
The existing agent and node EKS Auth permissions are reused. Controller region
and VPC ID are explicit so it does not depend on EC2 metadata. Keep controller
chart and official IAM policy versions aligned during future upgrades; review
upstream CRD upgrade instructions before updating an existing release.

The bootstrap Role allows only required Deployments, Services, ConfigMaps,
ServiceAccounts, Ingresses and Helm release Secrets within url-shortner, plus
Pod/ReplicaSet/Event reads. It does not grant exec, RBAC administration, namespace
creation, node access or kube-system access. Helm Secrets access is sensitive;
keep the environment approval and repository controls in place.

## 3. Optional initial application deployment by administrator

Select a full SHA already present in all three ECR repositories. Do not use
test-sha or latest. The following selects the newest frontend tag and stops if
that commit is not present in both backends; if that happens, choose the SHA of
a fully successful publishing run instead.

```bash
IMAGE_TAG=$(aws ecr describe-images --repository-name url-shortner-frontend \
  --query 'sort_by(imageDetails, &imagePushedAt)[-1].imageTags[0]' --output text)
[[ "$IMAGE_TAG" =~ ^[0-9a-f]{40}$ ]] || { echo "Select a full published Git SHA"; exit 1; }
for repository in url-shortner-frontend url-shortner-url-service url-shortner-analytics-service; do
  aws ecr describe-images --repository-name "$repository" \
    --image-ids imageTag="$IMAGE_TAG" --query 'imageDetails[].imageDigest' || exit 1
done
```

Then:

```bash
helm lint helm/url-shortner -f helm/url-shortner/values-nonprod.yaml --set-string image.tag="$IMAGE_TAG"
helm template url-shortner helm/url-shortner --namespace url-shortner \
  -f helm/url-shortner/values-nonprod.yaml --set-string image.tag="$IMAGE_TAG"
helm upgrade --install url-shortner helm/url-shortner --namespace url-shortner \
  -f helm/url-shortner/values-nonprod.yaml --set-string image.tag="$IMAGE_TAG" \
  --atomic --wait --timeout 10m
kubectl -n url-shortner wait --for=jsonpath='{.status.loadBalancer.ingress[0].hostname}' ingress/url-shortner --timeout=5m
ALB_HOST=$(kubectl -n url-shortner get ingress url-shortner -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
helm upgrade --install url-shortner helm/url-shortner --namespace url-shortner \
  -f helm/url-shortner/values-nonprod.yaml --set-string image.tag="$IMAGE_TAG" \
  --set-string publicBaseUrl="http://$ALB_HOST" --atomic --wait --timeout 5m
kubectl -n url-shortner get ingress url-shortner
kubectl -n url-shortner get deployments,pods,services
printf 'http://%s\n' "$ALB_HOST"
```

On initial provisioning, the second Helm reconciliation supplies the assigned hostname to PUBLIC_BASE_URL
so API responses also return public short URLs. It keeps the same images and
release, without rebuilding. CD reuses a known Ingress hostname on subsequent
rollouts and reconciles a second time only if the hostname changes. The frontend
already constructs same-origin links.
ALB reconciliation and target health are asynchronous; inspect controller logs,
Ingress events, subnet tags and Pod readiness if no hostname or healthy targets
appear. Helm --atomic waits for workloads, not for an ALB's targets to be healthy.

## 4. End-to-end checks through the public ALB

From a host with Internet access after targets are healthy:

```bash
curl --retry 10 --retry-delay 3 --retry-all-errors -fsS "http://$ALB_HOST/health"
curl -fsS "http://$ALB_HOST/"
CODE=$(curl -fsS "http://$ALB_HOST/api/urls" -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/kata"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["code"])')
curl -fsS "http://$ALB_HOST/api/urls/$CODE/stats"
curl -sS -D - -o /dev/null "http://$ALB_HOST/r/$CODE"
curl -fsS "http://$ALB_HOST/api/urls/$CODE/stats"
kubectl -n url-shortner get pods
```

Expect healthy/page responses, initial click count 0, a 302 Location pointing to
https://example.com/kata, and then click count 1. Open http://$ALB_HOST in a browser
to verify shortening, copy and statistics. Analytics remains internal even though
its statistics are exposed through the intended URL Service API.

HTTP is for this short-lived demonstration only: traffic is unencrypted and
unauthenticated at the transport layer. Production needs an appropriate domain,
an ACM certificate, HTTPS listener and HTTP-to-HTTPS redirect. ALB, public IPv4
and traffic incur charges in addition to existing EKS/NAT costs.

## 5. Automatic GitHub deployment after merging to main

The existing CI workflow runs lint/tests/builds/scans and publishes all three
images. Only after publish succeeds does the main-push-only deploy job request
approval for environment nonprod and run on the trusted private-network runner.
It assumes the separate deployment role, installs Helm 3/kubectl, validates the
chart and uses exactly github.sha for all image tags. It does not download or
execute workflow_run artifacts, rebuild images, run Terraform, create namespaces,
install the controller or deploy production. A per-environment concurrency group
serializes deployments. Atomic Helm operations roll back failed workload updates.

```bash
gh run list --repo mouslim21/url-shortner --workflow ci.yml --branch main --limit 3
gh run view RUN_ID --repo mouslim21/url-shortner --log
kubectl -n url-shortner get deployments \
  -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.template.spec.containers[0].image}{"\n"}{end}'
helm history url-shortner --namespace url-shortner
kubectl -n url-shortner get ingress url-shortner
```

Replace RUN_ID with the actual main-push run. Expect the exact triggering commit
SHA on all three images, completed rollout checks and the Ingress URL in logs.
Approve the environment deployment if configured. A new merged commit publishes
new immutable tags and updates Pod templates, triggering rollouts. Do not rerun
an older commit merely to redeploy an unrelated newer SHA. The CI workflow is
push/PR-triggered, so merging a new trusted commit is the normal CD trigger.

Blockers before automatic CD: manually applied IAM/access-entry prerequisites,
ready controller/agent, bootstrapped namespace RBAC, configured/protected nonprod
environment with AWS_DEPLOY_ROLE_ARN, a trusted private-network runner, and all
required CI/security/publishing checks passing. None of these runtime successes
is implied by static validation.
