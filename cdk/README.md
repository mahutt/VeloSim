## Prerequisites

- AWS CLI v2 authenticated to your AWS account in ca-central-1
- Node 20+, npm, AWS CDK v2 installed
- Docker with Buildx enabled and QEMU installed
- jq installed


## 1. Bootstrap CDK and deploy infrastructure with desiredCount=0

This deploy creates VPC, RDS Postgres, ECR repo velosim, ECS cluster and service, IAM
for GitHub Actions. We deploy with desiredCount=0 to avoid the image race on first
deploy.

Change desiredCount to 0 in cdk/lib/velosim-stack.ts

Replace ALLOWED_IPS with your public IP CIDR (can be `0.0.0.0/0` for all IPs).

```bash
git clone https://github.com/vinishamanek/VeloSim.git
cd VeloSim
git checkout feature/258-deploy-aws

AWS_REGION="ca-central-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION

ALLOWED_IPS="$(curl -s https://checkip.amazonaws.com)/32"
cdk deploy -c allowedIps='["'"$ALLOWED_IPS"'"]' -c mapboxAccessToken=""
```

Note:
- First deploy runs with desiredCount=0 in cdk/lib/velosim-stack.ts, otherwise the scale
  up will fail because the images are not in the container registry yet.
- We will scale the service to 1 after pushing images


## 2. Capture CDK outputs and instance IP

```bash
STACK_NAME="VeloSimStack"
AWS_REGION="ca-central-1"

ECR_REPO_URI=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryURI'].OutputValue" --output text)
DB_ENDPOINT=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" --output text)
DB_SECRET_ARN=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" --output text)
CLUSTER=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='ECSClusterName'].OutputValue" --output text)
SERVICE=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='ECSServiceName'].OutputValue" --output text)
ASG_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query "Stacks[0].Outputs[?OutputKey=='AutoScalingGroupName'].OutputValue" --output text)

EC2_INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$ASG_NAME" --region "$AWS_REGION" --query 'AutoScalingGroups[0].Instances[0].InstanceId' --output text)
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$EC2_INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "ECR_REPO_URI=$ECR_REPO_URI"
echo "DB_ENDPOINT=$DB_ENDPOINT"
echo "DB_SECRET_ARN=$DB_SECRET_ARN"
echo "CLUSTER=$CLUSTER"
echo "SERVICE=$SERVICE"
echo "PUBLIC_IP=$PUBLIC_IP"
```


## 3. Build and push images with Docker Buildx (linux/arm64)

We use the nginx same-origin proxy. The frontend will be built with an empty
VITE_BACKEND_URL so the browser calls /api and nginx proxies to backend:8000.

```bash
AWS_REGION="ca-central-1"
docker buildx create --use --name velosim-builder 2>/dev/null || true
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ECR_REPO_URI%/*}"
```

Build and push backend image to :latest

```bash
docker buildx build --platform linux/arm64 -t "${ECR_REPO_URI}:latest" -f back/Dockerfile . --push
```

Build and push osrm image to :osrm-latest

```bash
docker buildx build --platform linux/arm64 -t "${ECR_REPO_URI}:osrm-latest" -f docker/osrm/Dockerfile . --push
```

Build and push frontend image to :frontend-latest with empty backend URL

```bash
docker buildx build --platform linux/arm64 -t "${ECR_REPO_URI}:frontend-latest" -f front/Dockerfile \
  --build-arg VITE_MAPBOX_ACCESS_TOKEN="" \
  --build-arg VITE_BACKEND_URL="" \
  . --push
```

Build and push proxy image to :proxy-latest

```bash
docker buildx build --platform linux/arm64 -t "${ECR_REPO_URI}:proxy-latest" -f docker/nginx-proxy/Dockerfile docker/nginx-proxy --push
```

Note
- Ensure nginx.conf uses proxy_pass http://127.0.0.1:8000; under location /api/
- The frontend’s API client should use relative /api paths


## 4. Start the service and verify

Scale the service to 1 and force a rollout so it pulls the images just pushed.

```bash
AWS_REGION="ca-central-1"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --desired-count 1 --region "$AWS_REGION"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --force-new-deployment --region "$AWS_REGION"
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$AWS_REGION"
```

Verify in a browser by navigating to the public IP of the instance.

## 5. Run database migrations

The CDK includes a migration task definition family named velosim-migration that runs alembic upgrade head with the correct DB_* env and secrets.

```bash
AWS_REGION="ca-central-1"
MIGRATION_TASK_DEF=$(aws ecs list-task-definitions --family-prefix velosim-migration --sort DESC --region "$AWS_REGION" --query 'taskDefinitionArns[0]' --output text)

aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$MIGRATION_TASK_DEF" \
  --launch-type EC2 \
  --region "$AWS_REGION"

aws ecs list-tasks --cluster "$CLUSTER" --region "$AWS_REGION" --desired-status STOPPED --family velosim-migration --query 'taskArns[0]' --output text
```

Check CloudWatch Logs group /ecs/velosim-migrations for success if you configured that group. Otherwise, re-run with describe-tasks to view stoppedReason.

```bash
LAST_MIG_TASK=$(aws ecs list-tasks --cluster "$CLUSTER" --region "$AWS_REGION" --desired-status STOPPED --family velosim-migration --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster "$CLUSTER" --region "$AWS_REGION" --tasks "$LAST_MIG_TASK" --query 'tasks[0].{stoppedReason:stoppedReason,containers:containers[].{name:name,exitCode:exitCode,reason:reason}}' --output json
```


## 6. Seed the production database

Use the existing scripts/db_manager.py seed command inside the backend image, injecting the same DB_* environment used in production. Username and password are retrieved from Secrets Manager secret velosim/db-credentials. Host, port, and DB name come from CDK outputs.

```bash
AWS_REGION="ca-central-1"
SECRET_NAME="velosim/db-credentials"

CREDS_JSON=$(aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query SecretString --output text)
DB_USERNAME=$(echo "$CREDS_JSON" | jq -r '.username')
DB_PASSWORD=$(echo "$CREDS_JSON" | jq -r '.password')
DB_HOST="$DB_ENDPOINT"
DB_PORT="5432"
DB_NAME="velosim"

TASK_DEF_ARN=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$AWS_REGION" --query 'services[0].taskDefinition' --output text)

RUN_OUTPUT=$(aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$TASK_DEF_ARN" \
  --launch-type EC2 \
  --overrides "$(jq -n \
    --arg u "$DB_USERNAME" --arg p "$DB_PASSWORD" \
    --arg h "$DB_HOST" --arg port "$DB_PORT" --arg name "$DB_NAME" \
    '{ "containerOverrides": [ { "name": "backend", "environment": [
      { "name":"DB_USERNAME", "value":$u },
      { "name":"DB_PASSWORD", "value":$p },
      { "name":"DB_HOST", "value":$h },
      { "name":"DB_PORT", "value":$port },
      { "name":"DB_NAME", "value":$name }
    ], "command": ["python","scripts/db_manager.py","seed"] } ] }')" \
  --region "$AWS_REGION")

SEED_TASK_ARN=$(echo "$RUN_OUTPUT" | jq -r '.tasks[0].taskArn')
echo "$SEED_TASK_ARN"

aws ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$SEED_TASK_ARN" --region "$AWS_REGION"
aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$SEED_TASK_ARN" --region "$AWS_REGION" --query 'tasks[0].{stoppedReason:stoppedReason,containers:containers[].{name:name,exitCode:exitCode,reason:reason}}' --output json
```

Verify you can log in using the seeded credentials if the seed creates an admin user. If the seed inserts system data only, confirm expected tables are populated.
