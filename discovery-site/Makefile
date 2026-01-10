.PHONY: all init plan apply build sync invalidate deploy destroy cleanup-cli serve serve-test integration-test help

# Configuration
AWS_PROFILE ?= criticalwormholebrowser-prod
INFRA_DIR := infra
DIST_DIR := dist
BUCKET_NAME := criticalwormholebrowser-prod-discovery-256140316797
TEST_FIXTURES := ../browser-extension/tests/e2e/fixtures
DISCOVERY_URL := https://discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools

# CLI-created resources to clean up
CLI_CF_DISTRIBUTION := E1RR3W7GL1FN66
CLI_CF_OAC := E1P5SKUNVETL6F

export AWS_PROFILE

all: deploy

help:
	@echo "Discovery Site Deployment"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make init        - Initialize Terraform"
	@echo "  make plan        - Plan infrastructure changes"
	@echo "  make apply       - Apply infrastructure changes"
	@echo "  make destroy     - Destroy all infrastructure"
	@echo ""
	@echo "Deployment:"
	@echo "  make build       - Build the site"
	@echo "  make sync        - Sync built site to S3"
	@echo "  make invalidate  - Invalidate CloudFront cache"
	@echo "  make deploy      - Full deployment (infra + build + sync + invalidate)"
	@echo ""
	@echo "Local Testing:"
	@echo "  make serve            - Serve discovery site over wormhole"
	@echo "  make serve-test       - Serve test fixtures over wormhole"
	@echo "  make integration-test - Run integration tests against live discovery site"
	@echo ""
	@echo "Cleanup:"
	@echo "  make cleanup-cli - Remove CLI-created AWS resources"

# Terraform commands
init:
	cd $(INFRA_DIR) && terraform init

plan: init
	cd $(INFRA_DIR) && terraform plan

apply: init
	cd $(INFRA_DIR) && terraform apply -auto-approve

# Build commands
build:
	npm ci --prefer-offline 2>/dev/null || npm install
	npm run build

# Get outputs from Terraform
get-bucket-name:
	@cd $(INFRA_DIR) && terraform output -raw bucket_name 2>/dev/null || echo $(BUCKET_NAME)

get-distribution-id:
	@cd $(INFRA_DIR) && terraform output -raw cloudfront_distribution_id

# Sync to S3
sync: build
	@BUCKET=$$(cd $(INFRA_DIR) && terraform output -raw bucket_name 2>/dev/null || echo $(BUCKET_NAME)) && \
	echo "Syncing to s3://$$BUCKET" && \
	aws s3 sync $(DIST_DIR)/ s3://$$BUCKET/ --delete

# Invalidate CloudFront cache
invalidate:
	@DIST_ID=$$(cd $(INFRA_DIR) && terraform output -raw cloudfront_distribution_id) && \
	echo "Invalidating CloudFront distribution $$DIST_ID" && \
	aws cloudfront create-invalidation --distribution-id $$DIST_ID --paths "/*"

# Full deployment
deploy: apply sync invalidate
	@echo ""
	@echo "Deployment complete!"
	@cd $(INFRA_DIR) && terraform output site_url

# Serve discovery site over wormhole
serve: build
	@echo ""
	@echo "Serving discovery site over wormhole..."
	@echo "Connect using the code below at: $(DISCOVERY_URL)"
	@echo ""
	wh listen --serve $(DIST_DIR)

# Serve test fixtures over wormhole
serve-test:
	@echo ""
	@echo "Serving test fixtures over wormhole..."
	@echo "Connect using the code below at: $(DISCOVERY_URL)"
	@echo ""
	wh listen --serve $(TEST_FIXTURES)

# Run integration tests
integration-test:
	@echo "Running integration tests..."
	cd .. && python -m pytest tests/integration/test_discovery_site.py -v

# Destroy infrastructure
destroy:
	@echo "Emptying S3 bucket first..."
	-aws s3 rm s3://$(BUCKET_NAME)/ --recursive
	cd $(INFRA_DIR) && terraform destroy

# Cleanup CLI-created resources (run once before using Terraform)
cleanup-cli:
	@echo "Cleaning up CLI-created AWS resources..."
	@echo ""
	@echo "Step 1: Disabling CloudFront distribution $(CLI_CF_DISTRIBUTION)..."
	@if aws cloudfront get-distribution --id $(CLI_CF_DISTRIBUTION) 2>/dev/null; then \
		aws cloudfront get-distribution-config --id $(CLI_CF_DISTRIBUTION) --query 'DistributionConfig' > /tmp/cf-config.json && \
		jq '.Enabled = false' /tmp/cf-config.json > /tmp/cf-config-disabled.json && \
		ETAG=$$(aws cloudfront get-distribution-config --id $(CLI_CF_DISTRIBUTION) --query 'ETag' --output text) && \
		aws cloudfront update-distribution --id $(CLI_CF_DISTRIBUTION) --if-match "$$ETAG" --distribution-config file:///tmp/cf-config-disabled.json > /dev/null && \
		echo "Distribution disabled. Waiting for deployment (this takes a few minutes)..." && \
		aws cloudfront wait distribution-deployed --id $(CLI_CF_DISTRIBUTION) && \
		echo "Deleting distribution..." && \
		ETAG=$$(aws cloudfront get-distribution --id $(CLI_CF_DISTRIBUTION) --query 'ETag' --output text) && \
		aws cloudfront delete-distribution --id $(CLI_CF_DISTRIBUTION) --if-match "$$ETAG" && \
		echo "CloudFront distribution deleted."; \
	else \
		echo "CloudFront distribution $(CLI_CF_DISTRIBUTION) not found (already deleted)."; \
	fi
	@echo ""
	@echo "Step 2: Deleting CloudFront OAC $(CLI_CF_OAC)..."
	@if aws cloudfront get-origin-access-control --id $(CLI_CF_OAC) 2>/dev/null; then \
		ETAG=$$(aws cloudfront get-origin-access-control --id $(CLI_CF_OAC) --query 'ETag' --output text) && \
		aws cloudfront delete-origin-access-control --id $(CLI_CF_OAC) --if-match "$$ETAG" && \
		echo "OAC deleted."; \
	else \
		echo "OAC $(CLI_CF_OAC) not found (already deleted)."; \
	fi
	@echo ""
	@echo "Step 3: Deleting S3 bucket $(BUCKET_NAME)..."
	@if aws s3api head-bucket --bucket $(BUCKET_NAME) 2>/dev/null; then \
		aws s3 rb s3://$(BUCKET_NAME) --force && \
		echo "S3 bucket deleted."; \
	else \
		echo "S3 bucket $(BUCKET_NAME) not found (already deleted)."; \
	fi
	@echo ""
	@echo "Cleanup complete! You can now run 'make deploy' to create resources with Terraform."
