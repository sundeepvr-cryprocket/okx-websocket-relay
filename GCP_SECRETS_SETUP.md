# GitHub Secrets Setup for Google Cloud Deployment

## Prerequisites

1. Google Cloud Platform (GCP) Account
2. GitHub Repository
3. Google Cloud SDK installed locally
4. GitHub CLI (optional, but recommended)

## Step-by-Step GCP Service Account Creation

### 1. Create a Service Account

```bash
# Set your project ID
export PROJECT_ID=your-project-id

# Create service account
gcloud iam service-accounts create github-actions-deployer \
    --display-name "GitHub Actions Deployer"
```

### 2. Assign Necessary Roles

```bash
# Assign roles for Cloud Run deployment
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

# Container Registry access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Pub/Sub access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

# Logging access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

### 3. Generate Service Account Key

```bash
# Create JSON key file
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com
```

## GitHub Secrets Configuration

### Required Secrets

1. **GCP_PROJECT_ID**
   - Value: Your Google Cloud Project ID
   - How to set:
     ```bash
     gh secret set GCP_PROJECT_ID --body "$PROJECT_ID"
     ```

2. **GCP_SA_KEY**
   - Value: Entire contents of the `github-actions-key.json` file
   - How to set:
     ```bash
     gh secret set GCP_SA_KEY --body "$(cat github-actions-key.json)"
     ```

3. **SLACK_WEBHOOK** (Optional)
   - Value: Slack Webhook URL for deployment notifications
   - How to set:
     ```bash
     gh secret set SLACK_WEBHOOK --body "https://hooks.slack.com/services/..."
     ```

## Security Best Practices

1. **Rotate Service Account Keys**
   - Regenerate keys every 90 days
   - Use the principle of least privilege

2. **Limit Service Account Scope**
   - Only assign necessary roles
   - Avoid using project-wide admin roles

3. **Protect Sensitive Information**
   - Never commit service account keys to repository
   - Use GitHub Secrets for all sensitive data

## Verification Steps

1. Confirm Service Account Creation
   ```bash
   gcloud iam service-accounts list | grep github-actions-deployer
   ```

2. Verify Role Assignments
   ```bash
   gcloud projects get-iam-policy $PROJECT_ID \
     | grep github-actions-deployer
   ```

## Troubleshooting

### Common Issues

- **Permission Denied**: Ensure correct roles are assigned
- **Key Authentication Failure**: Regenerate service account key
- **Deployment Errors**: Check GitHub Actions logs

### Debugging Workflow

1. Check GitHub Actions tab in your repository
2. Review workflow run details
3. Examine specific job logs for error messages

## Recommended Next Steps

1. Set up two-factor authentication
2. Implement IP restrictions for service account
3. Use Workload Identity Federation for enhanced security

## Script for Automated Setup

```bash
#!/bin/bash

# Automated GCP and GitHub Secrets Setup
PROJECT_ID=$1
GITHUB_REPO=$2

# Validate inputs
if [ -z "$PROJECT_ID" ] || [ -z "$GITHUB_REPO" ]; then
    echo "Usage: $0 <project-id> <github-repo>"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Create service account
gcloud iam service-accounts create github-actions-deployer \
    --display-name "GitHub Actions Deployer"

# Assign roles (simplified for brevity)
ROLES=(
    "roles/run.admin"
    "roles/storage.admin"
    "roles/pubsub.publisher"
    "roles/logging.logWriter"
)

for ROLE in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="$ROLE"
done

# Generate key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com

# Set GitHub secrets
gh secret set GCP_PROJECT_ID --body "$PROJECT_ID" --repo "$GITHUB_REPO"
gh secret set GCP_SA_KEY --body "$(cat github-actions-key.json)" --repo "$GITHUB_REPO"

echo "Setup complete. Please manually set Slack webhook if needed."
```

## Disclaimer

Always review and understand the permissions you're granting. 
Consult your organization's security guidelines before implementation.
