# NPAID Peace Events Scraper - Deployment Guide

## 🎯 Overview

This guide walks you through deploying the NPAID peace events scraper system to Azure with GitHub Actions CI/CD.

## 📋 Prerequisites

### Required Accounts & Tools
- Azure subscription
- AWS account (for S3 and SNS)
- GitHub account
- Docker installed locally
- Azure CLI installed
- AWS CLI installed

### Required Permissions
- Azure: Contributor role on subscription
- AWS: S3 and SNS full access
- GitHub: Admin access to repository

## 🔧 Step-by-Step Setup

### 1. Azure Setup

#### 1.1 Create Resource Group
```bash
az login

az group create \
  --name npaid-peace-scrapers-rg \
  --location eastus
```

#### 1.2 Create Azure Container Registry
```bash
az acr create \
  --resource-group npaid-peace-scrapers-rg \
  --name npaidregistry \
  --sku Basic \
  --admin-enabled true

# Get credentials
az acr credential show --name npaidregistry
# Save the username and password for GitHub secrets
```

#### 1.3 Create Service Principal for GitHub Actions
```bash
az ad sp create-for-rbac \
  --name "npaid-github-actions" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/npaid-peace-scrapers-rg \
  --sdk-auth

# Save the entire JSON output for AZURE_CREDENTIALS secret
```

### 2. AWS Setup

#### 2.1 Create S3 Bucket
```bash
aws configure  # Configure AWS CLI

aws s3 mb s3://npaid-peace-events-data --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket npaid-peace-events-data \
  --versioning-configuration Status=Enabled
```

#### 2.2 Create SNS Topics
```bash
# Developer notifications
aws sns create-topic --name npaid-scraper-errors-dev
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:npaid-scraper-errors-dev \
  --protocol email \
  --notification-endpoint dev-team@data2bots.com

# Business notifications
aws sns create-topic --name npaid-scraper-errors-business
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:npaid-scraper-errors-business \
  --protocol email \
  --notification-endpoint business-team@data2bots.com
```

#### 2.3 Create IAM User for Scrapers
```bash
# Create IAM user
aws iam create-user --user-name npaid-scraper-service

# Attach policies
aws iam attach-user-policy \
  --user-name npaid-scraper-service \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-user-policy \
  --user-name npaid-scraper-service \
  --policy-arn arn:aws:iam::aws:policy/AmazonSNSFullAccess

# Create access keys
aws iam create-access-key --user-name npaid-scraper-service
# Save AccessKeyId and SecretAccessKey for GitHub secrets
```

### 3. GitHub Repository Setup

#### 3.1 Create Repository
```bash
# Initialize git repository
cd npaid-peace-scraper
git init
git add .
git commit -m "Initial commit: NPAID peace events scraper system"

# Create GitHub repository (via GitHub UI or CLI)
gh repo create data2bots/npaid-peace-scraper --private

# Push code
git remote add origin https://github.com/data2bots/npaid-peace-scraper.git
git branch -M main
git push -u origin main
```

#### 3.2 Configure GitHub Secrets

Go to: Repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Value | Source |
|------------|-------|--------|
| `AZURE_CREDENTIALS` | JSON from service principal | Step 1.3 |
| `ACR_USERNAME` | Azure Container Registry username | Step 1.2 |
| `ACR_PASSWORD` | Azure Container Registry password | Step 1.2 |
| `AWS_ACCESS_KEY_ID` | AWS access key | Step 2.3 |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Step 2.3 |
| `S3_BUCKET` | `npaid-peace-events-data` | Step 2.1 |
| `SNS_ARN_DEVELOPERS` | Developer SNS topic ARN | Step 2.2 |
| `SNS_ARN_BUSINESS` | Business SNS topic ARN | Step 2.2 |

### 4. First Deployment

#### 4.1 Test Local Build
```bash
cd scrapers

# Build Docker image
docker build \
  --build-arg SCRAPER_FOLDER=wanep_nigeria \
  --build-arg SCRAPER_METHOD=PUPPET \
  -t npaid-wanep-scraper:test \
  .

# Test run locally
docker run \
  -e ENV=dev \
  -e S3BUCKET=npaid-peace-events-data \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  npaid-wanep-scraper:test
```

#### 4.2 Deploy via GitHub Actions
```bash
# Push to main branch to trigger deployment
git add .
git commit -m "Deploy WANEP Nigeria scraper"
git push origin main

# Or manually trigger deployment
# Go to: Actions → Deploy Peace Events Scraper → Run workflow
```

#### 4.3 Verify Deployment
```bash
# Check container instances
az container list \
  --resource-group npaid-peace-scrapers-rg \
  --output table

# View logs
az container logs \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep_nigeria-instance

# Check S3 for output data
aws s3 ls s3://npaid-peace-events-data/peace_events/wanep_nigeria/
```

### 5. Schedule Scrapers

#### 5.1 Using Azure Logic Apps (Recommended)
```bash
# Create Logic App
az logic workflow create \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep-daily-scraper \
  --definition @logic-app-definition.json
```

**logic-app-definition.json:**
```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "Recurrence": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Day",
          "interval": 1,
          "schedule": {
            "hours": ["2"],
            "minutes": [0]
          }
        }
      }
    },
    "actions": {
      "Create_container": {
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connection": {
              "name": "@parameters('$connections')['azurecontainerinstance']['connectionId']"
            }
          },
          "method": "put",
          "path": "/subscriptions/{subscription-id}/resourceGroups/npaid-peace-scrapers-rg/providers/Microsoft.ContainerInstance/containerGroups/wanep-nigeria-scheduled"
        }
      }
    }
  }
}
```

#### 5.2 Using Cron Jobs (Alternative)
```bash
# On a Linux server
crontab -e

# Add line to run daily at 2 AM
0 2 * * * docker run npaidregistry.azurecr.io/wanep_nigeria:latest
```

### 6. Monitoring Setup

#### 6.1 Azure Monitor
```bash
# Enable container insights
az monitor log-analytics workspace create \
  --resource-group npaid-peace-scrapers-rg \
  --workspace-name npaid-scraper-logs

# Link to container instances
az container create \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep-nigeria-monitored \
  --image npaidregistry.azurecr.io/wanep_nigeria:latest \
  --log-analytics-workspace npaid-scraper-logs
```

#### 6.2 SNS Email Alerts
Already configured in Step 2.2. Test with:
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:npaid-scraper-errors-dev \
  --message "Test alert from NPAID scraper system"
```

### 7. Adding New Scrapers

#### 7.1 Create New Scraper
```bash
# Create folder structure
mkdir -p scrapers/leadership_ng
touch scrapers/leadership_ng/__init__.py
touch scrapers/leadership_ng/scraper.py
touch scrapers/leadership_ng/config.yml

# Implement scraper following wanep_nigeria template
```

#### 7.2 Deploy New Scraper
```bash
# Commit and push
git add scrapers/leadership_ng/
git commit -m "Add Leadership News scraper"
git push origin main

# Manually trigger deployment for specific scraper
# GitHub Actions → Run workflow → Enter scraper name: leadership_ng
```

## 🔍 Verification Checklist

After deployment, verify:

- [ ] Azure Container Registry contains images
- [ ] Container instances are running
- [ ] S3 bucket contains parquet files
- [ ] Hash files are being updated
- [ ] SNS notifications are working
- [ ] GitHub Actions workflows are passing
- [ ] Logs show successful scraping
- [ ] Data validation passes

## 🐛 Troubleshooting

### Container Fails to Start
```bash
# Check logs
az container logs \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep_nigeria-instance

# Check events
az container show \
  --resource-group npaid-peace-scrapers-rg \
  --name wanep_nigeria-instance \
  --query instanceView.events
```

### S3 Upload Fails
```bash
# Test AWS credentials
aws s3 ls s3://npaid-peace-events-data/

# Check IAM permissions
aws iam get-user-policy \
  --user-name npaid-scraper-service \
  --policy-name S3Access
```

### GitHub Actions Fails
```bash
# Check secrets are set correctly
# Repository → Settings → Secrets

# Verify Azure credentials
az login --service-principal \
  -u <appId> \
  -p <password> \
  --tenant <tenant>
```

## 📊 Cost Estimation

### Azure Costs (Monthly)
- Container Registry (Basic): ~$5
- Container Instances (1 CPU, 2GB RAM, 1 hour/day): ~$15
- Logic Apps (100 runs/month): ~$0.50
- **Total: ~$20/month**

### AWS Costs (Monthly)
- S3 Storage (10GB): ~$0.23
- S3 Requests: ~$0.05
- SNS: ~$0.50
- **Total: ~$1/month**

### Grand Total: ~$21/month

## 🔐 Security Best Practices

1. **Rotate credentials regularly**
   - Azure service principal: Every 90 days
   - AWS access keys: Every 90 days

2. **Use least privilege**
   - IAM policies should only grant necessary permissions
   - Azure RBAC should be scoped to resource group

3. **Enable logging**
   - Azure Monitor for container logs
   - AWS CloudTrail for S3 access logs

4. **Encrypt data**
   - S3 bucket encryption enabled
   - Azure Container Registry encryption enabled

## 📞 Support

For deployment issues:
- Check logs first
- Review GitHub Actions workflow logs
- Contact DevOps team: devops@data2bots.com

## 📚 Additional Resources

- [Azure Container Instances Documentation](https://docs.microsoft.com/azure/container-instances/)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Docker Documentation](https://docs.docker.com/)