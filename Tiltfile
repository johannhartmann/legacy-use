# Tiltfile for legacy-use development with Kind and local registry
# Based on https://docs.tilt.dev/example_helm.html

# Fail fast on errors
update_settings(max_parallel_updates=3)

# Configure file watching to ignore temp files and VM images
watch_settings(ignore=[
    '/tmp/**', 
    '/var/tmp/**', 
    'vms/**', 
    '*.qcow2', 
    '*.iso',
    'infra/docker/*/output/**',
    'infra/docker/legacy-use-windows-image-builder/output/**',
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

# Get environment variables and create a temporary values file with substituted values
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
legacy_use_api_key = os.getenv('LEGACY_USE_API_KEY', '')

# Create values override string
values_override = """
management:
  env:
    ANTHROPIC_API_KEY: "{}"
mcpServer:
  env:
    LEGACY_USE_API_KEY: "{}"
""".format(anthropic_api_key, legacy_use_api_key)

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
        'management.image.repository={}'.format(mgmt_image.rsplit(':', 1)[0]),
        'management.image.tag={}'.format(mgmt_image.rsplit(':', 1)[1] if ':' in mgmt_image else 'latest'),
        'mcpServer.image.repository={}'.format(mcp_image.rsplit(':', 1)[0]),
        'mcpServer.image.tag={}'.format(mcp_image.rsplit(':', 1)[1] if ':' in mcp_image else 'latest'),
        'wineTarget.image.repository={}'.format(wine_image.rsplit(':', 1)[0]),
        'wineTarget.image.tag={}'.format(wine_image.rsplit(':', 1)[1] if ':' in wine_image else 'latest'),
        'linuxTarget.image.repository={}'.format(linux_image.rsplit(':', 1)[0]),
        'linuxTarget.image.tag={}'.format(linux_image.rsplit(':', 1)[1] if ':' in linux_image else 'latest'),
        'androidTarget.image.repository={}'.format(android_image.rsplit(':', 1)[0]),
        'androidTarget.image.tag={}'.format(android_image.rsplit(':', 1)[1] if ':' in android_image else 'latest'),
        'windowsKubevirt.enabled={}'.format('true' if kubevirt_installed else 'false'),
    ]
))

# Configure individual k8s resources
k8s_resource(
    'legacy-use-database',
    port_forwards='5432:5432',
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
    port_forwards='3000:3000',
    labels=['core'],
    resource_deps=['legacy-use-mgmt']  # MCP depends on mgmt, which depends on database
)

k8s_resource(
    'legacy-use-wine-target',
    port_forwards=[
        '5900:5900',  # VNC
        '6080:6080',  # noVNC
    ],
    labels=['targets']
)

k8s_resource(
    'legacy-use-linux-target',
    port_forwards=[
        '5901:5900',  # VNC (mapped to avoid conflict)
        '6081:80',    # noVNC (mapped to avoid conflict)
    ],
    labels=['targets']
)

k8s_resource(
    'legacy-use-android-target',
    port_forwards=[
        '5555:5555',  # ADB
        '5902:5900',  # VNC (mapped to avoid conflict)
        '6082:6080',  # noVNC (mapped to avoid conflict)
    ],
    labels=['targets']
)

# Windows KubeVirt resources
if kubevirt_installed:
    # Windows image builder as a local resource
    local_resource(
        'windows-image-builder',
        cmd='docker build -t localhost:5000/legacy-use-windows-image-builder -f infra/docker/legacy-use-windows-image-builder/Dockerfile infra/docker/legacy-use-windows-image-builder && docker push localhost:5000/legacy-use-windows-image-builder',
        labels=['build'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )
    
    # Helper to build and upload Windows image
    local_resource(
        'windows-image-upload',
        cmd='./scripts/windows-kubevirt-setup.sh build && ./scripts/windows-kubevirt-setup.sh upload',
        labels=['build'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL,
        resource_deps=['windows-image-builder']
    )
    
    # Windows VM resources - Tilt doesn't automatically track VirtualMachineInstanceReplicaSet
    # For now, we'll just use local resources to manage the Windows VM
    # The VMIRS will be deployed by Helm but not tracked by Tilt's k8s_resource
    
    # Local resource to check Windows VM status
    local_resource(
        'windows-vm-status',
        cmd='kubectl get vmirs,vmi,pods,pvc -n legacy-use | grep windows || echo "No Windows VM resources found"',
        labels=['targets'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )
    
    # Local resource to manually create port forwards for Windows VM
    local_resource(
        'windows-vm-ports',
        serve_cmd='kubectl port-forward -n legacy-use svc/legacy-use-windows-kubevirt 3389:3389 5903:5900',
        labels=['targets'],
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )

# Local resource for generating API keys
local_resource(
    'generate-api-key',
    cmd='uv run python generate_api_key.py',
    labels=['tools']
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

# Print helpful information
print("""
Legacy-use Development Environment
==================================

Services will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8088
- MCP Server: http://localhost:3000/mcp
- PostgreSQL: localhost:5432

Container Targets:
- Wine Target VNC: vnc://localhost:5900 (password: wine)
- Wine Target noVNC: http://localhost:6080
- Linux Target VNC: vnc://localhost:5901 (password: password123)
- Linux Target noVNC: http://localhost:6081/static/vnc.html
- Android Target ADB: localhost:5555
- Android Target VNC: vnc://localhost:5902
- Android Target noVNC: http://localhost:6082""")

if kubevirt_installed:
    print("""
Windows KubeVirt Target (KubeVirt detected):
- Windows RDP: localhost:3389 (user: Admin, password: windows)
- Windows VNC: vnc://localhost:5903
- Windows noVNC: http://localhost:6083

To set up Windows VM:
1. Click "windows-image-builder" in Tilt UI to build the image
2. Click "windows-image-upload" to upload to PVC
3. The VM will start automatically""")
else:
    print("""
Windows KubeVirt Target: Not available (KubeVirt not installed)
To enable: Install KubeVirt in your cluster""")

print("""
To generate an API key:
- Click "generate-api-key" in the Tilt UI

To run database migrations:
- Click "db-migrations" in the Tilt UI

Hot reloading is enabled for:
- Frontend code (app/)
- Backend code (server/)
""")
