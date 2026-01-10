# Critical Wormhole Browser Implementation Guide

## Overview

**Application**: criticalwormholebrowser
**Domain**: `criticalwormhole.tools`
**Environments**: dev, prod

This guide documents the infrastructure provisioned by AWS Project Paver for the Critical Wormhole Browser application on the `criticalwormhole.tools` domain.

## Infrastructure Summary

### Domain Configuration

| Component | Value |
|-----------|-------|
| Parent Domain | `criticalwormhole.tools` |
| Apps Subdomain | `apps.criticalwormhole.tools` |
| Apps Zone ID | `Z09727391DOKHW98O91Y4` |

### IAM Role

| Property | Value |
|----------|-------|
| Role Name | `developer-app-criticalwormholebrowser` |
| Role ARN | `arn:aws:iam::256140316797:role/apps/developer-app-criticalwormholebrowser` |
| External ID | `criticalwormholebrowser-deployment` |

### Route53 Hosted Zones

| Environment | Zone Name | Zone ID |
|-------------|-----------|---------|
| Production | `criticalwormholebrowser.apps.criticalwormhole.tools` | `Z03667952UZ1NQEZBHI4F` |
| Dev | `dev.criticalwormholebrowser.apps.criticalwormhole.tools` | `Z09710101QYS87KJW1HD` |
| Prod | `prod.criticalwormholebrowser.apps.criticalwormhole.tools` | `Z09710111ZZGP299W8UMI` |

### ACM Certificates

| Environment | Domain | Certificate ARN |
|-------------|--------|-----------------|
| Production | `*.criticalwormholebrowser.apps.criticalwormhole.tools` | `arn:aws:acm:us-east-1:256140316797:certificate/1d0f8b40-e43a-4dbd-a644-0aa7ac643f9d` |
| Dev | `*.dev.criticalwormholebrowser.apps.criticalwormhole.tools` | `arn:aws:acm:us-east-1:256140316797:certificate/d3777e18-8a12-4778-86b8-7850a8cfbc47` |
| Prod | `*.prod.criticalwormholebrowser.apps.criticalwormhole.tools` | `arn:aws:acm:us-east-1:256140316797:certificate/e15f7a41-b13c-4529-8778-cabfa04c9664` |

### Secrets Manager

| Property | Value |
|----------|-------|
| Secret Name | `criticalwormholebrowser/paver-config` |
| Retrieve Command | `aws secretsmanager get-secret-value --secret-id criticalwormholebrowser/paver-config --query SecretString --output text \| jq` |

## AWS CLI Profile Configuration

Add the following profiles to your `~/.aws/config`:

```ini
[profile criticalwormholebrowser-dev]
region = us-east-1
output = json
role_arn = arn:aws:iam::256140316797:role/apps/developer-app-criticalwormholebrowser
source_profile = developer-user
external_id = criticalwormholebrowser-deployment

[profile criticalwormholebrowser-prod]
region = us-east-1
output = json
role_arn = arn:aws:iam::256140316797:role/apps/developer-app-criticalwormholebrowser
source_profile = developer-user
external_id = criticalwormholebrowser-deployment
```

### Test the Profile

```bash
# Test dev profile
aws sts get-caller-identity --profile criticalwormholebrowser-dev

# Expected output:
# {
#     "UserId": "AROAXXXXXXXXX:botocore-session-...",
#     "Account": "256140316797",
#     "Arn": "arn:aws:sts::256140316797:assumed-role/developer-app-criticalwormholebrowser/..."
# }
```

## Resource Naming Conventions

All resources must follow these naming patterns to work within the IAM policy constraints:

### S3 Buckets

```text
criticalwormholebrowser-{environment}-{purpose}-256140316797
```

Examples:

- `criticalwormholebrowser-dev-frontend-256140316797`
- `criticalwormholebrowser-prod-assets-256140316797`

### Lambda Functions

```text
criticalwormholebrowser-{environment}-{function-name}
```

Examples:

- `criticalwormholebrowser-dev-api`
- `criticalwormholebrowser-prod-handler`

### DynamoDB Tables

```text
criticalwormholebrowser-{environment}-{table-name}
```

Examples:

- `criticalwormholebrowser-dev-sessions`
- `criticalwormholebrowser-prod-data`

### CloudFormation Stacks

```text
criticalwormholebrowser-{environment}-{stack-purpose}
```

Examples:

- `criticalwormholebrowser-dev-infrastructure`
- `criticalwormholebrowser-prod-api`

## CDK Bootstrap Configuration

This app has not yet been CDK bootstrapped. To bootstrap CDK for this application:

### 1. Determine the CDK Qualifier

The qualifier is derived from the app name:

- App name: `criticalwormholebrowser`
- CDK qualifier: `criticalwormholebrowserbs`
- Bootstrap stack: `CDKToolkit-criticalwormholebrowserbs`

### 2. Bootstrap CDK

```bash
# Assume the app role
export AWS_PROFILE=criticalwormholebrowser-dev

# Bootstrap with app-specific qualifier
cdk bootstrap aws://256140316797/us-east-1 \
  --qualifier criticalwormholebrowserbs \
  --toolkit-stack-name CDKToolkit-criticalwormholebrowserbs
```

### 3. Configure CDK App

In your CDK app's `cdk.json`:

```json
{
  "app": "npx ts-node bin/app.ts",
  "context": {
    "@aws-cdk/core:bootstrapQualifier": "criticalwormholebrowserbs"
  }
}
```

### 4. Update Paver After Bootstrap

After bootstrapping, update the app in `terraform/terraform.tfvars`:

```hcl
criticalwormholebrowser = {
  description      = "Critical Wormhole Browser application"
  environments     = ["dev", "prod"]
  domains          = ["criticalwormhole.tools"]
  cdk_bootstrapped = true  # Change from false to true
  s3_buckets       = []
  dynamodb_tables  = []
}
```

Then apply the change:

```bash
cd /path/to/aws-project-paver/terraform
AWS_PROFILE=bootstrap terraform apply
```

## GitHub Actions CI/CD

The IAM role supports GitHub OIDC for CI/CD pipelines. Configure your workflow:

```yaml
name: Deploy

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::256140316797:role/apps/developer-app-criticalwormholebrowser
          aws-region: us-east-1

      - name: Deploy
        run: |
          # Your deployment commands here
          cdk deploy --all --require-approval never
```

## Retrieve Paver Configuration

Get the complete infrastructure configuration programmatically:

```bash
# Using AWS CLI
aws secretsmanager get-secret-value \
  --secret-id criticalwormholebrowser/paver-config \
  --query SecretString \
  --output text \
  --profile criticalwormholebrowser-dev | jq

# The secret contains:
# - IAM role ARN and details
# - ACM certificate ARNs for each environment
# - Route53 zone IDs and names
# - Naming conventions
# - CDK configuration
```

## Example: Creating a CloudFront Distribution

```bash
export AWS_PROFILE=criticalwormholebrowser-prod

# Use the production certificate
CERT_ARN="arn:aws:acm:us-east-1:256140316797:certificate/e15f7a41-b13c-4529-8778-cabfa04c9664"

# Create CloudFront distribution with the certificate
# The certificate covers *.prod.criticalwormholebrowser.apps.criticalwormhole.tools
```

## Example: Creating DNS Records

```bash
export AWS_PROFILE=criticalwormholebrowser-prod

# Production zone ID
ZONE_ID="Z09710111ZZGP299W8UMI"

# Create a CNAME record
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.prod.criticalwormholebrowser.apps.criticalwormhole.tools",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "d1234567890.cloudfront.net"}]
      }
    }]
  }'
```

## Troubleshooting

### Cannot Assume Role

If you get `AccessDenied` when assuming the role:

1. Verify your source profile has valid credentials:

   ```bash
   aws sts get-caller-identity --profile developer-user
   ```

2. Check the external ID is correct: `criticalwormholebrowser-deployment`

3. Verify the role exists:

   ```bash
   aws iam get-role --role-name developer-app-criticalwormholebrowser --profile bootstrap
   ```

### Permission Denied on Resources

The IAM role only allows access to resources with the `criticalwormholebrowser-` prefix. Ensure all resource names follow the naming conventions.

### CDK Deploy Fails

If CDK deployment fails:

1. Verify CDK is bootstrapped with the correct qualifier
2. Check `cdk.json` has the correct bootstrap qualifier
3. Ensure `cdk_bootstrapped = true` in the paver configuration

## Summary

| Resource | Identifier |
|----------|------------|
| Domain | `criticalwormhole.tools` |
| Role ARN | `arn:aws:iam::256140316797:role/apps/developer-app-criticalwormholebrowser` |
| External ID | `criticalwormholebrowser-deployment` |
| Production Zone | `Z03667952UZ1NQEZBHI4F` |
| Dev Zone | `Z09710101QYS87KJW1HD` |
| Prod Zone | `Z09710111ZZGP299W8UMI` |
| Production Cert | `arn:aws:acm:us-east-1:256140316797:certificate/1d0f8b40-e43a-4dbd-a644-0aa7ac643f9d` |
| Dev Cert | `arn:aws:acm:us-east-1:256140316797:certificate/d3777e18-8a12-4778-86b8-7850a8cfbc47` |
| Prod Cert | `arn:aws:acm:us-east-1:256140316797:certificate/e15f7a41-b13c-4529-8778-cabfa04c9664` |
| Config Secret | `criticalwormholebrowser/paver-config` |
