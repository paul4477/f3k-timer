#!/bin/bash

###############################################################################
# enumerate_usb_serial.sh
# 
# Enumerates all current USB serial devices and creates udev rules to fix 
# their device names based on vendor ID, product ID, and serial number.
#
# Usage:
#   ./enumerate_usb_serial.sh [--create] [--reload]
#
# Options:
#   --create    Write the generated rules to /etc/udev/rules.d/99-usb-serial.rules
#   --reload    Reload udev rules after creating (requires --create and sudo)
#
###############################################################################

set -euo pipefail

CREATE_RULES=false
RELOAD_RULES=false
RULES_FILE="/etc/udev/rules.d/99-usb-serial.rules"
TEMP_RULES_FILE="/tmp/99-usb-serial.rules.tmp"

# Parse command line arguments
INTERACTIVE=true
DEVICE_NAMES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --create)
            CREATE_RULES=true
            shift
            ;;
        --reload)
            RELOAD_RULES=true
            shift
            ;;
        --name)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --name requires an argument"
                exit 1
            fi
            # Store comma-separated names
            IFS=',' read -ra DEVICE_NAMES <<< "$2"
            INTERACTIVE=false
            shift 2
            ;;
        --batch)
            INTERACTIVE=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --create              Write rules to $RULES_FILE"
            echo "  --reload              Reload udev rules (requires --create and sudo)"
            echo "  --name <names>        Device names (comma-separated for multiple devices)"
            echo "                        If not specified, you'll be prompted for each device"
            echo "  --batch               Skip interactive prompts, use calculated names"
            echo "  --help                Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running with appropriate privileges for --create
if [[ "$CREATE_RULES" == true ]] && [[ ! -w "$RULES_FILE" ]] && [[ ! -w "/etc/udev/rules.d/" ]]; then
    if [[ $EUID -ne 0 ]]; then
        echo "Error: Creating udev rules requires sudo"
        exit 1
    fi
fi

echo "=========================================="
echo "USB Serial Device Enumeration"
echo "=========================================="
echo ""

# Initialize rules file content
RULES_CONTENT="# USB Serial Device Rules"
RULES_CONTENT+=$'\n'"# Auto-generated on $(date)"
RULES_CONTENT+=$'\n'"# This file assigns persistent symlinks to USB serial devices"
RULES_CONTENT+=$'\n'"# based on their Vendor ID, Product ID, and Serial Number"
RULES_CONTENT+=$'\n'"#"
RULES_CONTENT+=$'\n'""

DEVICE_COUNT=0

# Find all ttyUSB devices
for tty_device in /dev/ttyUSB* /dev/ttyACM*; do
    if [[ -e "$tty_device" ]]; then
        echo "Found device: $tty_device"
        
        # Get device information
        UDEV_INFO=$(udevadm info --name="$tty_device" --attribute-walk 2>/dev/null || echo "")
        
        # Extract attributes
        VENDOR=$(echo "$UDEV_INFO" | grep -m 1 'ATTRS{idVendor}' | awk -F'"' '{print $2}' || echo "UNKNOWN")
        PRODUCT=$(echo "$UDEV_INFO" | grep -m 1 'ATTRS{idProduct}' | awk -F'"' '{print $2}' || echo "UNKNOWN")
        SERIAL=$(echo "$UDEV_INFO" | grep -m 1 'ATTRS{serial}' | awk -F'"' '{print $2}' || echo "UNKNOWN")
        MANUFACTURER=$(echo "$UDEV_INFO" | grep -m 1 'ATTRS{manufacturer}' | awk -F'"' '{print $2}' || echo "UNKNOWN")
        PRODUCT_NAME=$(echo "$UDEV_INFO" | grep -m 1 'ATTRS{product}' | awk -F'"' '{print $2}' || echo "UNKNOWN")
        
        # Sanitize device name (replace special characters)
        DEVICE_NAME=$(echo "$PRODUCT_NAME" | tr ' ' '_' | tr -cd 'a-zA-Z0-9_-' || echo "serial_device")
        if [[ -z "$DEVICE_NAME" ]]; then
            DEVICE_NAME="serial_device"
        fi
        
        # Append index if name is generic or empty
        if [[ "$DEVICE_NAME" == "serial_device" ]]; then
            DEVICE_NAME="${DEVICE_NAME}_${DEVICE_COUNT}"
        fi
        
        # Display device details
        echo "  Device Name:      $tty_device"
        echo "  Vendor ID:        $VENDOR"
        echo "  Product ID:       $PRODUCT"
        echo "  Serial Number:    $SERIAL"
        echo "  Manufacturer:     $MANUFACTURER"
        echo "  Product:          $PRODUCT_NAME"
        echo "  Suggested Name:   /dev/$DEVICE_NAME"
        echo ""
        
        # Get device name from --name parameter if provided, otherwise prompt user
        if [[ "$INTERACTIVE" == true ]]; then
            read -p "Confirm device name [$DEVICE_NAME] or enter alternative: " USER_INPUT
            if [[ -n "$USER_INPUT" ]]; then
                DEVICE_NAME="$USER_INPUT"
            fi
        elif [[ ${#DEVICE_NAMES[@]} -gt $DEVICE_COUNT && -n "${DEVICE_NAMES[$DEVICE_COUNT]}" ]]; then
            DEVICE_NAME="${DEVICE_NAMES[$DEVICE_COUNT]}"
        fi
        echo ""
        
        # Build udev rule - prefer serial number, fall back to vendor+product
        if [[ "$SERIAL" != "UNKNOWN" ]]; then
            RULE="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"$VENDOR\", ATTRS{idProduct}==\"$PRODUCT\", ATTRS{serial}==\"$SERIAL\", SYMLINK+=\"$DEVICE_NAME\", MODE=\"0666\""
        else
            RULE="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"$VENDOR\", ATTRS{idProduct}==\"$PRODUCT\", SYMLINK+=\"$DEVICE_NAME\", MODE=\"0666\""
        fi
        
        # Add rule to content
        RULES_CONTENT+=$'\n'"# Device: $PRODUCT_NAME ($tty_device)"
        RULES_CONTENT+=$'\n'"$RULE"
        RULES_CONTENT+=$'\n'""
        
        DEVICE_COUNT=$((DEVICE_COUNT + 1))
    fi
done

if [[ $DEVICE_COUNT -eq 0 ]]; then
    echo "No USB serial devices found."
    exit 0
fi

echo "=========================================="
echo "Generated udev rules ($DEVICE_COUNT device(s)):"
echo "=========================================="
echo "$RULES_CONTENT"
echo ""

# Write rules if requested
if [[ "$CREATE_RULES" == true ]]; then
    echo "Writing rules to $RULES_FILE..."
    
    # Write to temp file first
    echo "$RULES_CONTENT" > "$TEMP_RULES_FILE"
    
    # Move to actual location with sudo if needed
    if [[ ! -w "/etc/udev/rules.d/" ]]; then
        sudo mv "$TEMP_RULES_FILE" "$RULES_FILE"
    else
        mv "$TEMP_RULES_FILE" "$RULES_FILE"
    fi
    
    echo "✓ Rules written to $RULES_FILE"
    echo ""
    
    # Reload rules if requested
    if [[ "$RELOAD_RULES" == true ]]; then
        echo "Reloading udev rules..."
        if [[ $EUID -ne 0 ]]; then
            sudo udevadm control --reload-rules
            sudo udevadm trigger
        else
            udevadm control --reload-rules
            udevadm trigger
        fi
        echo "✓ udev rules reloaded"
        echo ""
        echo "Disconnect and reconnect your USB serial devices to apply the new symlinks."
    else
        echo ""
        echo "To reload the rules, run:"
        echo "  sudo udevadm control --reload-rules"
        echo "  sudo udevadm trigger"
        echo ""
        echo "Then disconnect and reconnect your USB serial devices."
    fi
else
    echo "To apply these rules, save them to $RULES_FILE and reload udev:"
    echo ""
    echo "  sudo tee $RULES_FILE > /dev/null << 'EOF'"
    echo "$RULES_CONTENT"
    echo "EOF"
    echo ""
    echo "  sudo udevadm control --reload-rules"
    echo "  sudo udevadm trigger"
    echo ""
    echo "Or run this script with --create --reload flags to do it automatically:"
    echo "  sudo $0 --create --reload"
    echo ""
    echo "To skip interactive prompts:"
    echo "  $0 --batch --create --reload"
    echo ""
    echo "To specify device names directly (comma-separated for multiple):"
    echo "  $0 --name device1,device2 --create --reload"
fi
