#!/bin/bash
# QEMU wrapper script to add Apple SMC device for macOS VMs

# Log all invocations
echo "[$(date)] QEMU wrapper called with args: $@" >> /var/log/qemu-wrapper.log

# Check if this looks like a macOS VM by examining the command line
# Look for OVMF firmware or specific disk names
NEEDS_SMC=false

for arg in "$@"; do
    if [[ "$arg" == *"OVMF"* ]] || [[ "$arg" == *"OpenCore"* ]] || [[ "$arg" == *"macos"* ]]; then
        NEEDS_SMC=true
        break
    fi
done

if [ "$NEEDS_SMC" = true ]; then
    echo "[$(date)] Detected macOS VM, adding Apple SMC device" >> /var/log/qemu-wrapper.log
    # Find the original QEMU binary
    if [ -f /usr/libexec/qemu-kvm.orig ]; then
        QEMU_BIN="/usr/libexec/qemu-kvm.orig"
    elif [ -f /usr/bin/qemu-system-x86_64.orig ]; then
        QEMU_BIN="/usr/bin/qemu-system-x86_64.orig"
    elif [ -f /usr/libexec/qemu-system-x86_64.orig ]; then
        QEMU_BIN="/usr/libexec/qemu-system-x86_64.orig"
    else
        echo "Error: Could not find original QEMU binary" >> /var/log/qemu-wrapper.log
        exit 1
    fi
    # Execute real QEMU with additional Apple SMC device
    exec "$QEMU_BIN" \
        -device "isa-applesmc,osk=ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc" \
        "$@"
else
    # Not a macOS VM, execute normally
    if [ -f /usr/libexec/qemu-kvm.orig ]; then
        exec /usr/libexec/qemu-kvm.orig "$@"
    elif [ -f /usr/bin/qemu-system-x86_64.orig ]; then
        exec /usr/bin/qemu-system-x86_64.orig "$@"
    elif [ -f /usr/libexec/qemu-system-x86_64.orig ]; then
        exec /usr/libexec/qemu-system-x86_64.orig "$@"
    else
        echo "Error: Could not find original QEMU binary" >> /var/log/qemu-wrapper.log
        exit 1
    fi
fi