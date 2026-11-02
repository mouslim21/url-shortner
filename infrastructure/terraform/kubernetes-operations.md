# Step 7: Pod Identity and Helm operations

These are manual deployment instructions. The coding agent has not applied
Terraform, installed a Helm release or changed Kubernetes resources.

## Infrastructure first

From the repository root, using the existing administrator profile:

```bash
export AWS_PROFILE=kata-dev
export AWS_REGION=us-east-1
terraform -chdir=infrastructure/terraform/environments/nonprod init
terraform -chdir=infrastructure/terraform/environments/nonprod validate
terraform -chdir=infrastructure/terraform/environments/nonprod plan -out=pod-identity.tfplan
```

Review the entire plan. Only after approval, run:

```bash
terraform -chdir=infrastructure/terraform/environments/nonprod apply pod-identity.tfplan
aws eks update-kubeconfig --name url-shortner-nonprod-eks --region us-east-1
kubectl -n kube-system rollout status daemonset/eks-pod-identity-agent --timeout=180s
kubectl -n kube-system get pods -l app.kubernetes.io/name=eks-pod-identity-agent
aws eks list-pod-identity-associations --cluster-name url-shortner-nonprod-eks
terraform -chdir=infrastructure/terraform/environments/nonprod output workload_role_arns
terraform -chdir=infrastructure/terraform/environments/nonprod output pod_identity_association_ids
```

Expect a ready agent on each node and two associations in namespace
`url-shortner`, for ServiceAccounts `url-service` and `analytics-service`.
Associations may be created before their Kubernetes namespace/ServiceAccounts.
The existing AmazonEKSWorkerNodePolicy supplies `eks-auth:AssumeRoleForPodIdentity`;
no DynamoDB permissions are granted to the node role. New policies grant only
GetItem/PutItem on short_urls and GetItem/UpdateItem on url_analytics, respectively.
Trust uses pods.eks.amazonaws.com, AssumeRole/TagSession and exact cluster,
namespace and ServiceAccount session-tag conditions.

The private EKS endpoint requires VPC connectivity, or an explicitly enabled
public endpoint restricted to the administrator's actual public CIDR. Do not
widen IAM or Kubernetes permissions to resolve network reachability issues.

## Select an image tag present in all three repositories

Use a full SHA from a successful image-publishing run. This retrieves the newest
frontend tag, then checks that the same tag exists for both backends. If any
check fails, stop and choose a SHA from a fully successful publishing run instead
of deploying a partially published commit.

```bash
IMAGE_TAG=$(aws ecr describe-images --repository-name url-shortner-frontend \
  --query 'sort_by(imageDetails, &imagePushedAt)[-1].imageTags[0]' --output text)
[[ "$IMAGE_TAG" =~ ^[0-9a-f]{40}$ ]] || { echo "Select a full published Git SHA"; exit 1; }
for repository in url-shortner-frontend url-shortner-url-service url-shortner-analytics-service; do
  aws ecr describe-images --repository-name "$repository" \
    --image-ids imageTag="$IMAGE_TAG" --query 'imageDetails[].imageDigest' || exit 1
done
```

## Chart validation and manual installation

The chart has no dependencies. `test-sha` is a render-only placeholder; do not
install it. No Ingress, ALB, HPA or application CD is configured.

```bash
helm lint helm/url-shortner
helm template url-shortner helm/url-shortner --namespace url-shortner \
  -f helm/url-shortner/values-nonprod.yaml --set image.tag=test-sha
```

Only after the infrastructure checks above pass, install manually:

```bash
helm upgrade --install url-shortner helm/url-shortner \
  --namespace url-shortner --create-namespace \
  -f helm/url-shortner/values-nonprod.yaml \
  --set-string image.tag="$IMAGE_TAG" --wait --timeout 5m

for deployment in frontend url-service analytics-service; do
  kubectl -n url-shortner rollout status "deployment/$deployment" --timeout=180s
done
kubectl -n url-shortner get serviceaccounts
kubectl -n url-shortner get deployments,pods,services
kubectl -n url-shortner logs deployment/url-service --tail=100
kubectl -n url-shortner logs deployment/analytics-service --tail=100
```

`--create-namespace` creates the namespace first; Helm orders ServiceAccounts
before Deployments. Their fixed names match the Terraform associations. Pod
Identity injects its own projected token and credential-provider settings;
normal Kubernetes API token automount is disabled. No IRSA role annotation or
static AWS credentials are needed. Do not rename the namespace or backend
ServiceAccounts without updating Terraform associations and trust conditions.

The frontend listens on 8080 behind a ClusterIP Service on 80. Backends use
8000. All workloads run non-root, drop capabilities, prohibit privilege
escalation, use RuntimeDefault seccomp and have read-only root filesystems with
bounded /tmp emptyDirs. Nginx uses a mounted config and directly starts nginx,
bypassing the stock entrypoint's configuration writes. All Nginx temporary paths
and its PID are under /tmp. The resolver defaults to the standard kube-dns Service
FQDN; override frontend.dnsResolver if the cluster uses a different DNS Service.
All three services initially have one replica; requests total 250m CPU/320Mi.
Health probes call /health, which does not depend on DynamoDB readiness.

Optional identity verification, without printing credentials:

```bash
kubectl -n url-shortner exec deployment/url-service -- python -c \
  'import boto3; print(boto3.client("sts").get_caller_identity()["Arn"])'
kubectl -n url-shortner exec deployment/analytics-service -- python -c \
  'import boto3; print(boto3.client("sts").get_caller_identity()["Arn"])'
```

Expect distinct workload role names, not the node or GitHub publishing role.
For credentials errors, check the agent, association names, role trust, SDK
credential provider and IAM table ARNs. Backends disable EC2 metadata fallback.
For ImagePullBackOff, verify the same immutable tag exists in each repository,
node ECR pull permissions and NAT connectivity. For frontend startup errors,
inspect its logs, mounted config, DNS Service and /tmp volume permissions.

## End-to-end checks through the frontend

In one terminal:

```bash
kubectl -n url-shortner port-forward service/frontend 8080:80
```

In a second terminal:

```bash
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:8080/
CODE=$(curl -fsS http://localhost:8080/api/urls \
  -H 'Content-Type: application/json' -d '{"url":"https://example.com/kata"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["code"])')
curl -fsS "http://localhost:8080/api/urls/$CODE/stats"
curl -sS -D - -o /dev/null "http://localhost:8080/r/$CODE"
curl -fsS "http://localhost:8080/api/urls/$CODE/stats"
```

Expect healthy/page responses, initial count 0, HTTP 302 with Location
https://example.com/kata, then count 1. This verifies both workload identities,
DynamoDB writes/reads and internal analytics HTTP communication. The UI uses
same-origin paths. publicBaseUrl defaults to localhost:8080 for port-forward
verification; set the actual frontend origin when public routing is added later.

## Manual analytics resilience test

Keep the port-forward terminal running. The subshell restores the original
replica count even if a check fails. Do not run this against an environment
where temporarily stopping analytics is unacceptable.

```bash
(
  ORIGINAL_REPLICAS=$(kubectl -n url-shortner get deployment analytics-service -o jsonpath='{.spec.replicas}')
  trap 'kubectl -n url-shortner scale deployment/analytics-service --replicas="$ORIGINAL_REPLICAS"' EXIT
  kubectl -n url-shortner scale deployment/analytics-service --replicas=0
  kubectl -n url-shortner wait --for=delete pod \
    -l app.kubernetes.io/component=analytics-service --timeout=120s
  curl -sS -D - -o /dev/null "http://localhost:8080/r/$CODE"
  curl -sS -o /dev/null -w '%{http_code}\n' "http://localhost:8080/api/urls/$CODE/stats"
)
kubectl -n url-shortner rollout status deployment/analytics-service --timeout=180s
curl -sS -o /dev/null -w '%{http_code}\n' "http://localhost:8080/r/$CODE"
curl -fsS "http://localhost:8080/api/urls/$CODE/stats"
```

During the outage, expect redirect 302 and stats 503; unavailable analytics does
not block redirects indefinitely (HTTP timeout defaults to 0.3 seconds). After
recovery, expect stats 200 and click counting to resume. Failed click-recording
requests are best effort and are not replayed.
