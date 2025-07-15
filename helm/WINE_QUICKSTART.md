# Wine Container Quick Start Guide

This guide shows how to deploy legacy-use with Wine container support on Kubernetes.

## Prerequisites

- Kubernetes cluster
- Helm 3.0+
- kubectl configured

## Quick Deploy

```bash
# 1. Add legacy-use helm repository (if public)
# helm repo add legacy-use https://charts.legacy-use.com
# helm repo update

# 2. Install with Wine support
helm install legacy-use . -n legacy-use --create-namespace \
  -f values-production.yaml \
  -f values-wine.yaml

# 3. Wait for Wine container to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=wine-target -n legacy-use --timeout=300s
```

## Access Wine Container

### Via Web Browser
```bash
# Port forward to access Wine desktop
kubectl port-forward -n legacy-use deployment/legacy-use-wine-target 6080:6080

# Open in browser
open http://localhost:6080/vnc.html
# Password: wine
```

### Via VNC Client
```bash
# Port forward VNC
kubectl port-forward -n legacy-use deployment/legacy-use-wine-target 5900:5900

# Connect with VNC client
vncviewer localhost:5900
# Password: wine
```

## Install Windows Applications

### Method 1: Copy and Install
```bash
# Copy installer to Wine container
kubectl cp myapp.exe legacy-use/legacy-use-wine-target:/home/wineuser/apps/

# Install via web interface
# 1. Open http://localhost:6080/vnc.html
# 2. Open terminal in Wine desktop
# 3. Run: wine /home/wineuser/apps/myapp.exe
```

### Method 2: Example Applications
```bash
# Install Notepad++
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  bash -c "
    cd /home/wineuser/apps
    wget -O notepad++.exe 'https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.5.8/npp.8.5.8.Installer.exe'
    wine notepad++.exe /S
  "

# Install 7-Zip
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  bash -c "
    cd /home/wineuser/apps
    wget -O 7z.exe 'https://www.7-zip.org/a/7z2301-x64.exe'
    wine 7z.exe /S
  "
```

## Create Legacy-Use Target

Once Wine is running, create a target in legacy-use:

```json
{
  "name": "Wine Applications",
  "type": "vnc",
  "host": "legacy-use-wine-target",
  "port": 5900,
  "password": "wine",
  "width": 1920,
  "height": 1080
}
```

## Configuration Options

### Enable Wine with Custom Settings
```yaml
# values-wine-custom.yaml
wineTarget:
  enabled: true
  
  # Resource allocation
  resources:
    limits:
      cpu: 4
      memory: 4Gi
    requests:
      cpu: 1
      memory: 1Gi
  
  # Persistent storage
  persistence:
    enabled: true
    size: 20Gi
    storageClass: "fast-ssd"
  
  # Node placement
  nodeSelector:
    wine-enabled: "true"
```

### Enable Web Access via Ingress
```yaml
# values-wine-ingress.yaml
wineTarget:
  enabled: true
  
  ingress:
    enabled: true
    className: "nginx"
    hosts:
      - host: wine.your-domain.com
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: wine-novnc
                port:
                  number: 6080
    tls:
      - secretName: wine-tls
        hosts:
          - wine.your-domain.com
```

## Troubleshooting

### Check Wine Container Status
```bash
# Check pod status
kubectl get pods -n legacy-use -l app.kubernetes.io/component=wine-target

# Check logs
kubectl logs -n legacy-use deployment/legacy-use-wine-target
```

### Wine Application Issues
```bash
# Check Wine status
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  ps aux | grep -E "(wine|Xvfb|vnc)"

# Check Wine configuration
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  wine --version
```

### Access Issues
```bash
# Test VNC connectivity
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  nc -zv localhost 5900

# Test noVNC
kubectl exec -it deployment/legacy-use-wine-target -n legacy-use -- \
  curl -I http://localhost:6080
```

## Scaling and Performance

### Horizontal Scaling
```yaml
wineTarget:
  replicas: 3  # Run multiple Wine instances
```

### Resource Optimization
```yaml
wineTarget:
  resources:
    limits:
      cpu: 2
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 512Mi
```

## Security Considerations

1. **Change default password**: Update Wine VNC password
2. **Network policies**: Restrict access to Wine container
3. **Resource limits**: Prevent resource exhaustion
4. **Ingress security**: Add authentication for web access

## Next Steps

1. Install your Windows applications
2. Create legacy-use targets
3. Test automation workflows
4. Set up monitoring and logging
5. Configure backup for persistent data