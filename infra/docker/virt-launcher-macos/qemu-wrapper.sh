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
    # Execute real QEMU with additional Apple SMC device
    exec /usr/bin/qemu-system-x86_64.orig \
        -device "isa-applesmc,osk=ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc" \
        "$@"
else
    # Not a macOS VM, execute normally
    exec /usr/bin/qemu-system-x86_64.orig "$@"
fi