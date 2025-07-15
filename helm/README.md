# Legacy Use Helm Chart

This Helm chart deploys the Legacy Use application to Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Docker images available (either built locally or from GitHub Container Registry)

## Installation

### Using GitHub Container Registry Images (Recommended)

Once the GitHub Actions workflow has run and pushed images to ghcr.io:

```bash
# Install with production values
helm install legacy-use . -n legacy-use --create-namespace -f values-production.yaml

# Or upgrade existing installation
helm upgrade legacy-use . -n legacy-use -f values-production.yaml
```

### Using Local Images

If you have built images locally:

```bash
# Build images first
cd ..
./build_all_docker.sh

# Install with default values (uses local images)
helm install legacy-use . -n legacy-use --create-namespace
```

## Configuration

Key configuration options in `values.yaml`:

- `backend.image.repository` - Backend Docker image repository
- `backend.image.tag` - Backend Docker image tag
- `frontend.image.repository` - Frontend Docker image repository  
- `frontend.image.tag` - Frontend Docker image tag
- `ingress.enabled` - Enable/disable ingress
- `ingress.hosts` - Configure ingress hostnames

## Accessing the Application

After installation, the application will be available at:
- Frontend: http://<ingress-host>/
- Backend API: http://<ingress-host>/api

If ingress is disabled, use port-forwarding:

```bash
# Frontend
kubectl port-forward -n legacy-use svc/legacy-use-frontend 8080:80

# Backend
kubectl port-forward -n legacy-use svc/legacy-use-backend 8088:8088
```

## Uninstall

```bash
helm uninstall legacy-use -n legacy-use
```