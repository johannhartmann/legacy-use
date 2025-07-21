# Kind with KubeVirt Setup Guide

This guide explains how to set up a local Kubernetes cluster using Kind with KubeVirt support for running virtual machines.

## Prerequisites

Before starting, ensure you have the following installed:

1. **Docker** - Container runtime
   ```bash
   # Check if Docker is installed
   docker --version
   ```

2. **Kind** - Kubernetes in Docker
   ```bash
   # Install Kind
   curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
   chmod +x ./kind
   sudo mv ./kind /usr/local/bin/kind
   
   # Verify installation
   kind --version
   ```

3. **kubectl** - Kubernetes CLI
   ```bash
   # Install kubectl
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   
   # Verify installation
   kubectl version --client
   ```

## Quick Start

1. **Create Kind cluster with KubeVirt and local registry**:
   ```bash
   ./scripts/kind-setup.sh
   ```

2. **Check KubeVirt status**:
   ```bash
   ./scripts/check-kubevirt.sh
   ```

3. **Start Tilt development environment** (optional):
   ```bash
   ./scripts/tilt-up.sh
   # Access Tilt UI: http://localhost:10350
   ```

4. **Delete cluster when done**:
   ```bash
   ./scripts/kind-teardown.sh
   ```

See [Kind + Tilt Development Guide](./kind-tilt-development.md) for detailed development instructions.

## Detailed Setup

### 1. Cluster Configuration

The `kind-config.yaml` file configures the Kind cluster with:

- **Multi-node setup**: Control plane + worker node for better resource distribution
- **Local registry support**: Containerd configured to use localhost:5001 registry
- **Extra mounts**: Required device access for KubeVirt (`/dev`, `/boot`, `/lib/modules`)
- **Port mappings**: For accessing VMs, services, and development ports (8088, 5173, VNC ports)
- **Feature gates**: Kubernetes features required by KubeVirt

### 2. KubeVirt Installation

The setup script automatically:

1. Creates a local Docker registry on port 5001
2. Creates the Kind cluster with proper configuration
3. Configures all nodes to use the local registry
4. Installs KubeVirt operator and Custom Resource Definitions
5. Detects hardware virtualization support
6. Enables emulation mode if running in a nested virtualization environment
7. Installs the `virtctl` CLI tool for VM management

### 3. Hardware Virtualization

KubeVirt can run in two modes:

- **Hardware Virtualization**: Uses CPU virtualization extensions (Intel VT-x/AMD-V)
- **Emulation Mode**: Software emulation when hardware virtualization is unavailable

The setup script automatically detects and configures the appropriate mode.

## Creating Virtual Machines

### Example: Simple Linux VM

Create a file `test-vm.yaml`:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: testvm
spec:
  running: true
  template:
    metadata:
      labels:
        kubevirt.io/vm: testvm
    spec:
      domain:
        devices:
          disks:
          - name: containerdisk
            disk:
              bus: virtio
          - name: cloudinitdisk
            disk:
              bus: virtio
        resources:
          requests:
            memory: 1Gi
            cpu: "1"
      volumes:
      - name: containerdisk
        containerDisk:
          image: quay.io/containerdisks/fedora:latest
      - name: cloudinitdisk
        cloudInitNoCloud:
          userData: |
            #cloud-config
            users:
            - name: fedora
              lock_passwd: false
              passwd: $6$rounds=4096$salty$password
              sudo: ALL=(ALL) NOPASSWD:ALL
```

Apply the VM:
```bash
kubectl apply -f test-vm.yaml
```

### Accessing VMs

1. **Console access**:
   ```bash
   virtctl console testvm
   ```

2. **VNC access**:
   ```bash
   virtctl vnc testvm
   ```

3. **SSH access** (if configured):
   ```bash
   # Get VM IP
   kubectl get vmi testvm -o jsonpath='{.status.interfaces[0].ipAddress}'
   ```

## Legacy-use Integration

To use Kind+KubeVirt with legacy-use:

1. **Deploy legacy-use targets as VMs**: Convert Docker containers to VM images
2. **Use KubeVirt CDI**: For importing existing disk images
3. **Configure networking**: Use Kubernetes Services to expose VNC/RDP ports
4. **Scale with Kubernetes**: Use VM pools and autoscaling

### Example: Windows VM for Legacy-use

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: windows-legacy-target
spec:
  running: true
  template:
    spec:
      domain:
        cpu:
          cores: 2
        devices:
          disks:
          - name: windows-disk
            disk:
              bus: virtio
        resources:
          requests:
            memory: 4Gi
            cpu: "2"
      volumes:
      - name: windows-disk
        persistentVolumeClaim:
          claimName: windows-pvc
```

## Troubleshooting

### Common Issues

1. **KubeVirt not deploying**:
   ```bash
   # Check operator logs
   kubectl logs -n kubevirt deployment/virt-operator
   
   # Check component status
   kubectl get all -n kubevirt
   ```

2. **VMs not starting**:
   ```bash
   # Check VM status
   kubectl describe vm <vm-name>
   
   # Check virt-handler logs
   kubectl logs -n kubevirt -l kubevirt.io=virt-handler
   ```

3. **No hardware virtualization**:
   ```bash
   # Check CPU flags
   grep -E 'vmx|svm' /proc/cpuinfo
   
   # Enable emulation mode
   kubectl -n kubevirt patch kubevirt kubevirt --type=merge \
     --patch '{"spec":{"configuration":{"developerConfiguration":{"useEmulation":true}}}}'
   ```

### Useful Commands

```bash
# List all VMs
kubectl get vms,vmis --all-namespaces

# Get VM details
kubectl describe vm <vm-name>

# Delete a VM
kubectl delete vm <vm-name>

# Get KubeVirt version
kubectl get kubevirt -n kubevirt -o jsonpath='{.status.observedKubeVirtVersion}'

# Check KubeVirt status
kubectl get kubevirt -n kubevirt -o jsonpath='{.status.phase}'
```

## Advanced Configuration

### Custom Network Configuration

For legacy-use targets that need specific network setups:

```yaml
spec:
  template:
    spec:
      networks:
      - name: default
        pod: {}
      - name: legacy-net
        multus:
          networkName: legacy-network
      interfaces:
      - name: default
        masquerade: {}
      - name: legacy-net
        bridge: {}
```

### Resource Limits

Configure resource limits for VMs:

```yaml
spec:
  template:
    spec:
      domain:
        resources:
          requests:
            memory: 2Gi
            cpu: "1"
          limits:
            memory: 4Gi
            cpu: "2"
```

### Persistent Storage

Use PVCs for persistent VM storage:

```yaml
volumes:
- name: data-disk
  persistentVolumeClaim:
    claimName: vm-data-pvc
```

## Next Steps

1. **Containerized Disk Images**: Learn about creating custom OS images
2. **CDI (Containerized Data Importer)**: Import existing VM images
3. **Live Migration**: Move running VMs between nodes
4. **VM Snapshots**: Backup and restore VM states

## References

- [KubeVirt Documentation](https://kubevirt.io/user-guide/)
- [Kind Documentation](https://kind.sigs.k8s.io/)
- [KubeVirt on Kind Quickstart](https://kubevirt.io/quickstart_kind/)