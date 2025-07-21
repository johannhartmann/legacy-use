# Android Target for Legacy-Use

This container provides an Android emulator target for legacy-use automation.

## ⚠️ Important: KVM Requirement

The Android emulator requires KVM (Kernel-based Virtual Machine) for hardware acceleration. This means:

### Where it works:
- ✅ **Bare metal Kubernetes clusters** with KVM-enabled nodes
- ✅ **Virtual machines** with nested virtualization enabled
- ✅ **Docker on Linux** with KVM support (`--device /dev/kvm`)

### Where it doesn't work:
- ❌ **Kind (Kubernetes in Docker)** - No KVM support in containerized environments
- ❌ **Most cloud Kubernetes services** (EKS, GKE, AKS) - No KVM access
- ❌ **Docker Desktop on macOS/Windows** - No KVM support

## Running Locally with Docker

If you have KVM support on your host, you can run the Android target locally:

```bash
docker run -d \
  --name android-emulator \
  --device /dev/kvm \
  -p 5555:5555 \
  -p 5900:5900 \
  -p 6080:6080 \
  legacy-use-android-target
```

## Alternatives for Environments without KVM

1. **Use a cloud device farm** (BrowserStack, Sauce Labs, etc.)
2. **Connect physical Android devices** via ADB over network
3. **Use Genymotion** or other emulators that support software rendering
4. **Run on a bare metal Kubernetes cluster** with KVM-enabled nodes

## Checking KVM Support

To check if your environment supports KVM:

```bash
# On the host
ls -la /dev/kvm

# Check CPU virtualization support
egrep -c '(vmx|svm)' /proc/cpuinfo
```

## Configuration

The container uses the following environment variables:
- `EMULATOR_DEVICE`: Device profile (default: "Samsung Galaxy S10")
- `WEB_VNC`: Enable web-based VNC access (default: "true")
- `EMULATOR_ARGS`: Additional emulator arguments

## Troubleshooting

If the emulator fails to start, check the logs for:
- "KVM requires a CPU that supports vmx or svm"
- "x86 emulation currently requires hardware acceleration!"

These indicate missing KVM support.