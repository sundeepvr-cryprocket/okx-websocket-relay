#!/bin/bash

# Automated GCP and GitHub Secrets Setup Script

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check dependencies
check_dependencies() {
    local deps=("gcloud" "gh" "jq")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            echo -e "${RED}Error: $dep is not installed${NC}"
            exit 1
        fi
    done
}

# Validate input
validate_input() {
    if [ -z "$PROJECT_ID" ] || [ -z "$GITHUB_REPO" ]; then
        echo -e "${RED}Usage: ./setup_gcp_secrets.sh <project-id> <github-repo>${NC}"
        echo -e "Example: ./setup_gcp_secrets.sh my-project-123 myorg/myrepo"
        exit 1
    fi
}

# Setup service account
setup_service_account() {
    echo -e "${YELLOW}Creating GitHub Actions Service Account...${NC}"
    
    # Create service account
    gcloud iam service-accounts create github-actions-deployer \
        --display-name "GitHub Actions Deployer" || exit 1

    # Define roles
    local roles=(
        "roles/run.admin"
        "roles/storage.admin"
        "roles/pubsub.publisher"
        "roles/logging.logWriter"
        "roles/monitoring.viewer"
    )

    # Assign roles
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
            --role="$role" || exit 1
    done

    echo -e "${GREEN}Service account created and roles assigned successfully${NC}"
}

# Generate service account key
generate_service_key() {
    echo -e "${YELLOW}Generating service account key...${NC}"
    
    # Create key file
    gcloud iam service-accounts keys create github-actions-key.json \
        --iam-account="github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" || exit 1

    # Verify key was created
    if [ ! -f "github-actions-key.json" ]; then
        echo -e "${RED}Failed to create service account key${NC}"
        exit 1
    fi

    echo -e "${GREEN}Service account key generated successfully${NC}"
}

# Set GitHub secrets
set_github_secrets() {
    echo -e "${YELLOW}Setting up GitHub secrets...${NC}"
    
    # Set project ID secret
    gh secret set GCP_PROJECT_ID \
        --body "$PROJECT_ID" \
        --repo "$GITHUB_REPO" || exit 1

    # Set service account key secret
    gh secret set GCP_SA_KEY \
        --body "$(cat github-actions-key.json)" \
        --repo "$GITHUB_REPO" || exit 1

    # Optional: Slack webhook setup prompt
    read -p "Do you want to set up a Slack webhook for notifications? (y/n): " slack_choice
    if [[ "$slack_choice" =~ ^[Yy]$ ]]; then
        read -p "Enter your Slack webhook URL: " slack_webhook
        gh secret set SLACK_WEBHOOK \
            --body "$slack_webhook" \
            --repo "$GITHUB_REPO" || exit 1
    fi

    echo -e "${GREEN}GitHub secrets set up successfully${NC}"
}

# Cleanup sensitive files
cleanup() {
    echo -e "${YELLOW}Cleaning up sensitive files...${NC}"
    rm -f github-actions-key.json
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Main execution
main() {
    # Input parameters
    PROJECT_ID=$1
    GITHUB_REPO=$2

    # Validate and run
    check_dependencies
    validate_input
    
    # Confirm with user
    echo -e "${YELLOW}About to setup GCP service account and GitHub secrets for:${NC}"
    echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
    echo -e "GitHub Repo: ${GREEN}$GITHUB_REPO${NC}"
    read -p "Confirm? (y/n): " confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        setup_service_account
        generate_service_key
        set_github_secrets
        cleanup
        
        echo -e "${GREEN}🎉 GCP and GitHub Secrets Setup Complete! 🎉${NC}"
    else
        echo -e "${RED}Setup cancelled${NC}"
        exit 1
    fi
}

# Run main with arguments
main "$@"
