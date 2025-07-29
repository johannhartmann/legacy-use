# Secrets Management

This document describes how to properly manage secrets in the legacy-use application following 12-factor app principles.

## Overview

All sensitive configuration values (API keys, passwords, credentials) must be provided via environment variables and never hardcoded in source code or container images.

## Required Environment Variables

### Application Secrets

- `ANTHROPIC_API_KEY` - API key for Anthropic Claude (required for AI functionality)
- `API_KEY` - API key for authenticating with the legacy-use backend
- `AWS_ACCESS_KEY_ID` - AWS access key (only if using Bedrock provider)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (only if using Bedrock provider)
- `VERTEX_PROJECT_ID` - Google Cloud project ID (only if using Vertex provider)

### Database Secrets

- `POSTGRES_PASSWORD` - PostgreSQL database password
- `POSTGRES_USER` - PostgreSQL database user (default: postgres)
- `POSTGRES_DATABASE` - PostgreSQL database name (default: legacy_use_demo)

## Local Development

For local development, create a `.env` file based on `.env.template`:

```bash
cp .env.template .env
# Edit .env with your actual values
```

## Kubernetes Deployment

### Using Tilt (Development)

Tilt automatically creates Kubernetes secrets from your environment variables:

```bash
export ANTHROPIC_API_KEY="your-key-here"
export API_KEY="your-api-key"
export POSTGRES_PASSWORD="secure-password"

make tilt-up
```

### Using Helm (Production)

1. Create the API secrets:
```bash
kubectl create secret generic legacy-use-secrets \
  --from-literal=anthropic-api-key="$ANTHROPIC_API_KEY" \
  --from-literal=api-key="$API_KEY" \
  --namespace=legacy-use
```

2. Create the database secret:
```bash
kubectl create secret generic legacy-use-database-secret \
  --from-literal=postgres-password="$POSTGRES_PASSWORD" \
  --from-literal=postgres-user="postgres" \
  --from-literal=postgres-database="legacy_use_demo" \
  --namespace=legacy-use
```

3. Deploy with Helm:
```bash
helm install legacy-use ./infra/helm \
  --namespace=legacy-use \
  --values=infra/helm/values-production.yaml
```

## Security Best Practices

1. **Never commit secrets** - Use `.gitignore` to exclude `.env` files
2. **Use strong passwords** - Generate secure random passwords for production
3. **Rotate secrets regularly** - Update secrets periodically
4. **Limit access** - Use Kubernetes RBAC to control secret access
5. **Audit usage** - Monitor secret access in production

## Auto-configuration

When both `ANTHROPIC_API_KEY` and `API_KEY` are set in the environment:
- The frontend will automatically detect and use these credentials
- No manual API key entry or onboarding wizard is required
- The system will be ready to use immediately after deployment

## Troubleshooting

### Missing API Key Error
If the backend fails to start with a missing API_KEY error:
- Ensure the `API_KEY` environment variable is set
- Check that the Kubernetes secret was created correctly
- Verify the secret is mounted in the deployment

### Database Connection Errors
If database connection fails:
- Verify the database secret exists
- Check that the password matches what PostgreSQL expects
- Ensure the secret keys match: `postgres-password`, `postgres-user`, `postgres-database`