# Tiltfile for legacy-use development with Kind and local registry
# Based on https://docs.tilt.dev/example_helm.html

# Limit parallel updates to prevent resource contention
update_settings(max_parallel_updates=2)

# Configure file watching to ignore temp files and VM images
watch_settings(ignore=[
    '/tmp/**', 
    '/var/tmp/**', 
    'vms/**', 
    '*.qcow2', 
    '*.iso',
    'infra/docker/*/output/**',
    '**/*.log'
])

# Load extensions
load('ext://restart_process', 'docker_build_with_restart')
load('ext://helm_resource', 'helm_resource', 'helm_repo')

# Configuration
k8s_namespace = 'legacy-use'
# Using local registry on standard port
local_registry = 'localhost:5000'

# Windows KubeVirt detection - check if KubeVirt is available
kubevirt_check = str(local('kubectl get crd virtualmachines.kubevirt.io 2>/dev/null || echo "not-found"', quiet=True))
kubevirt_installed = "not-found" not in kubevirt_check

if not kubevirt_installed:
    print("KubeVirt not detected - Windows VM target will not be available")
else:
    print("KubeVirt detected - Windows VM target will be available")

# VM Cleanup - manual cleanup for orphaned VMs
local_resource(
    'vm-cleanup',
    cmd='''
        echo "Cleaning up orphaned VMs..."
        pkill -f virt-launcher || true
        pkill -f "qemu.*legacy-use" || true  
        pkill -f "samsung_galaxy_s10" || true
        echo "VM cleanup complete"
    ''',
    labels=['tools'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

# Ensure namespace exists
k8s_yaml(blob("""
apiVersion: v1
kind: Namespace
metadata:
  name: {}
""".format(k8s_namespace)))

# Docker builds with local registry
def docker_build_local(name, context, dockerfile, **kwargs):
    """Build Docker image and push to local registry"""
    # Tilt automatically handles the registry detection and tagging
    image = '{}/{}'.format(local_registry, name)
    
    # Standard build for all images
    docker_build(
        image,
        context,
        dockerfile=dockerfile,
        **kwargs
    )
    
    return image

# Build all Docker images
mgmt_image = docker_build_local(
    'legacy-use-mgmt',
    '.',
    'infra/docker/legacy-use-mgmt/Dockerfile'
)

mcp_image = docker_build_local(
    'legacy-use-mcp-server',
    '.',
    'infra/docker/legacy-use-mcp/Dockerfile'
)

wine_image = docker_build_local(
    'legacy-use-wine-target',
    '.',
    'infra/docker/legacy-use-wine-target/Dockerfile'
)

linux_image = docker_build_local(
    'linux-machine',
    '.',
    'infra/docker/linux-machine/Dockerfile'
)

android_image = docker_build_local(
    'legacy-use-android-target',
    '.',
    'infra/docker/legacy-use-android-target/Dockerfile'
)

novnc_proxy_image = docker_build_local(
    'legacy-use-novnc-proxy',
    'infra/docker/legacy-use-novnc-proxy',
    'infra/docker/legacy-use-novnc-proxy/Dockerfile'
)

# Get environment variables and create a temporary values file with substituted values
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
legacy_use_api_key = os.getenv('LEGACY_USE_API_KEY', os.getenv('API_KEY', ''))

# Create/update Kubernetes secret from environment variables
if anthropic_api_key or legacy_use_api_key:
    print("Creating/updating Kubernetes secret for API keys...")
    secret_cmd = (
        "kubectl create secret generic legacy-use-secrets " +
        "--from-literal=anthropic-api-key='{}' ".format(anthropic_api_key) +
        "--from-literal=api-key='{}' ".format(legacy_use_api_key) +
        "--namespace={} ".format(k8s_namespace) +
        "--dry-run=client -o yaml | kubectl apply -f -"
    )
    local(secret_cmd, quiet=True)

# Create values override string
# If we have secrets, use existingSecret; otherwise use env vars
if anthropic_api_key or legacy_use_api_key:
    values_override = """
management:
  existingSecret: legacy-use-secrets
mcpServer:
  existingSecret: legacy-use-secrets
"""
else:
    values_override = """
management:
  env:
    ANTHROPIC_API_KEY: "{}"
    API_KEY: "{}"
mcpServer:
  env:
    LEGACY_USE_API_KEY: "{}"
""".format(anthropic_api_key, legacy_use_api_key, legacy_use_api_key)

# Write temporary values file outside of watched paths
override_file = '/var/tmp/tilt-values-override.yaml'
local('echo \'{}\' > {}'.format(values_override, override_file))

# Always use base tilt values
values_files = ['infra/helm/values-tilt.yaml', override_file]

# Deploy Helm chart using k8s_yaml for individual resource control
k8s_yaml(helm(
    'infra/helm',
    name='legacy-use',
    namespace=k8s_namespace,
    values=values_files,
    set=[
        'windowsXpKubevirt.enabled={}'.format('true' if kubevirt_installed else 'false'),
        'windows10Kubevirt.enabled={}'.format('true' if kubevirt_installed else 'false'),
        'macosMojaveKubevirt.enabled={}'.format('true' if kubevirt_installed else 'false'),
    ]
))

# Configure individual k8s resources
k8s_resource(
    'legacy-use-database',
    labels=['database']
)

k8s_resource(
    'legacy-use-mgmt',
    port_forwards=[
        '8088:8088',  # Backend API
        '5173:5173',  # Frontend
    ],
    labels=['core'],
    resource_deps=['legacy-use-database']
)

k8s_resource(
    'legacy-use-mcp-server',
    port_forwards='5174:3000',
    labels=['core'],
    resource_deps=['legacy-use-android-target']  # Start after all container targets
)

k8s_resource(
    'legacy-use-wine-target',
    labels=['targets'],
    resource_deps=['legacy-use-mgmt', 'legacy-use-database']
)

k8s_resource(
    'legacy-use-linux-target',
    labels=['targets'],
    resource_deps=['legacy-use-wine-target']  # Start after Wine target
)

k8s_resource(
    'legacy-use-android-target',
    labels=['targets'],
    resource_deps=['legacy-use-linux-target']  # Start after Linux target
)

k8s_resource(
    'legacy-use-novnc-proxy',
    port_forwards='8090:80',  # noVNC proxy
    labels=['core'],
    resource_deps=['legacy-use-mgmt']
)

# Windows KubeVirt resources
if kubevirt_installed:
    # Note: VirtualMachineInstanceReplicaSets are not tracked by Tilt as k8s_resources
    # They are deployed by Helm but we can't use k8s_resource to manage dependencies
    # Instead, we'll use local_resources for monitoring and control
    
    # Start Windows XP VM
    local_resource(
        'windows-xp-vm-start',
        cmd='''
            echo "Starting Windows XP VM..."
            kubectl scale vmirs -n legacy-use legacy-use-windows-xp-vmirs --replicas=1 2>/dev/null || true
            echo "Waiting for Windows XP VMI to be created..."
            kubectl wait --for=jsonpath='{.status.replicas}'=1 vmirs/legacy-use-windows-xp-vmirs -n legacy-use --timeout=60s 2>/dev/null || true
        ''',
        labels=['vms'],
        auto_init=True,
        resource_deps=['legacy-use-wine-target', 'legacy-use-linux-target', 'legacy-use-android-target']
    )
    
    # Start Windows 10 VM after Windows XP
    local_resource(
        'windows-10-vm-start',
        cmd='''
            echo "Starting Windows 10 VM..."
            kubectl scale vmirs -n legacy-use legacy-use-windows-10-vmirs --replicas=1 2>/dev/null || true
            echo "Waiting for Windows 10 VMI to be created..."
            kubectl wait --for=jsonpath='{.status.replicas}'=1 vmirs/legacy-use-windows-10-vmirs -n legacy-use --timeout=60s 2>/dev/null || true
        ''',
        labels=['vms'],
        auto_init=True,
        resource_deps=['windows-xp-vm-start']
    )
    
    # Start macOS Mojave VM after Windows 10
    local_resource(
        'macos-mojave-vm-start',
        cmd='''
            echo "Starting macOS Mojave VM..."
            kubectl scale vmirs -n legacy-use legacy-use-macos-mojave-vmirs --replicas=1 2>/dev/null || true
            echo "Waiting for macOS Mojave VMI to be created..."
            kubectl wait --for=jsonpath='{.status.replicas}'=1 vmirs/legacy-use-macos-mojave-vmirs -n legacy-use --timeout=60s 2>/dev/null || true
            echo "All VMs started. Checking status..."
            kubectl get vmirs -n legacy-use
        ''',
        labels=['vms'],
        auto_init=True,
        resource_deps=['windows-10-vm-start']
    )
    
    # Manual VM operations
    local_resource(
        'vm-restart-all',
        cmd='''
            echo "Restarting all VMs..."
            kubectl delete vmi -n legacy-use --all --wait=true 2>/dev/null || true
            kubectl scale vmirs -n legacy-use --all --replicas=0 2>/dev/null || true
            sleep 5
            kubectl scale vmirs -n legacy-use --all --replicas=1 2>/dev/null || true
            echo "VM restart initiated - Tilt dependencies will handle the sequencing"
        ''',
        labels=['tools'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )
    
    
    # Local resource to check Windows VM status
    local_resource(
        'windows-vm-status',
        cmd='kubectl get vmirs,vmi,pods,pvc -n legacy-use | grep windows || echo "No Windows VM resources found"',
        labels=['targets'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL,
        resource_deps=['legacy-use-mgmt']
    )
    
    
    # Windows 10 VM resources
    local_resource(
        'windows-10-vm-status',
        cmd='kubectl get vmirs,vmi,pods,pvc -n legacy-use | grep windows-10 || echo "No Windows 10 VM resources found"',
        labels=['targets'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL,
        resource_deps=['legacy-use-mgmt']
    )
    
    
    # macOS Mojave VM resources
    local_resource(
        'macos-mojave-vm-status',
        cmd='kubectl get vmirs,vmi,pods,pvc -n legacy-use | grep mojave || echo "No macOS Mojave VM resources found"',
        labels=['targets'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL,
        resource_deps=['legacy-use-mgmt']
    )
    
    # macOS doesn't have RDP, so no port forwarding needed - use noVNC proxy
    
    # Scale VMs tool
    local_resource(
        'scale-vmirs',
        cmd='''
            echo "Scaling all VirtualMachineInstanceReplicaSets to 1 replica..."
            kubectl scale vmirs -n legacy-use --all --replicas=1
            echo ""
            echo "Current VMIRS status:"
            kubectl get vmirs -n legacy-use
        ''',
        labels=['tools'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )

# Local resource for generating API keys
local_resource(
    'generate-api-key',
    cmd='uv run python generate_api_key.py',
    labels=['tools']
)

# Local resource to show current API key from Kubernetes secret
local_resource(
    'show-api-key',
    cmd='kubectl get secret legacy-use-secrets -n legacy-use -o jsonpath=\'{.data.api-key}\' 2>/dev/null | base64 -d | xargs -I {} echo -e "\\n🔑 Current API Key: {}\\n\\n📋 Usage:\\n1. Open http://localhost:5173\\n2. Enter this API key when prompted\\n\\n💡 Or set in your environment:\\nexport API_KEY={}"',
    labels=['tools'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

# UI buttons for common tasks
local_resource(
    'frontend-lint',
    cmd='npm run lint',
    labels=['tools'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

local_resource(
    'backend-format',
    cmd='uv run ruff format . && uv run ruff check . --fix',
    labels=['tools'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

local_resource(
    'db-migrations',
    cmd='cd server && uv run alembic upgrade head',
    labels=['tools'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

# Print helpful information
print("""
Legacy-use Development Environment
==================================

Services will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8088
- MCP Server: http://localhost:5174/mcp
- noVNC Proxy: http://localhost:8090

Container Targets:
- Wine Target: Access via Management UI or noVNC proxy (http://localhost:8090)
- Linux Target: Access via Management UI or noVNC proxy (http://localhost:8090)
- Android Target: Access via Management UI or noVNC proxy (http://localhost:8090)""")

if kubevirt_installed:
    print("""
Windows & macOS KubeVirt Targets (KubeVirt detected):
- Windows XP VM: Access via Management UI or noVNC proxy (http://localhost:8090)
- Windows 10 VM: Access via Management UI or noVNC proxy (http://localhost:8090)
- macOS Mojave VM: Access via Management UI or noVNC proxy (http://localhost:8090)
  
Note: VMs start with staggered timing to reduce resource spikes
  - Windows XP (1GB) → 30s → Windows 10 (2GB) → 30s → macOS Mojave (4GB)
  - Use 'vm-restart-sequenced' to manually restart VMs with proper sequencing""")
else:
    print("""
Windows KubeVirt Targets: Not available (KubeVirt not installed)
To enable: Install KubeVirt in your cluster""")

print("""
To view the current API key:
- Click "show-api-key" in the Tilt UI

To generate a new API key:
- Click "generate-api-key" in the Tilt UI

To run database migrations:
- Click "db-migrations" in the Tilt UI

Hot reloading is enabled for:
- Frontend code (app/)
- Backend code (server/)
""")
