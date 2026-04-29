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

# Initialize arrays early to avoid unbound variable errors with set -u
declare -A EXISTING_RULES
declare -A PROCESSED_SIGNATURES
declare -A SIGNATURE_DEVICES
declare -a DUPLICATE_WARNINGS
EXISTING_RULES_COUNT=0
DUPLICATE_WARNINGS_COUNT=0

# Parse command line arguments
INTERACTIVE=true
DEVICE_NAMES=()

# Function to read existing rules and extract device signatures
read_existing_rules() {
    if [[ ! -f "$RULES_FILE" ]]; then
        return
    fi
    
    local current_signature=""
    local current_rule=""
    
    while IFS= read -r line; do
        # Skip comments and empty lines at the start
        if [[ $line =~ ^# ]]; then
            current_signature=""
            continue
        fi
        
        if [[ -z "$line" ]]; then
            if [[ -n "$current_signature" && -n "$current_rule" ]]; then
                EXISTING_RULES["$current_signature"]="$current_rule"
                EXISTING_RULES_COUNT=$((EXISTING_RULES_COUNT + 1))
                current_signature=""
                current_rule=""
            fi
            continue
        fi
        
        # Extract signature from rule (idVendor and idProduct)
        if [[ $line =~ ATTRS\{idVendor\}==\"([^\"]+)\" ]]; then
            local vendor="${BASH_REMATCH[1]}"
            if [[ $line =~ ATTRS\{idProduct\}==\"([^\"]+)\" ]]; then
                local product="${BASH_REMATCH[1]}"
                
                # Check if rule has serial number
                if [[ $line =~ ATTRS\{serial\}==\"([^\"]+)\" ]]; then
                    local serial="${BASH_REMATCH[1]}"
                    current_signature="${vendor}:${product}:${serial}"
                else
                    current_signature="${vendor}:${product}"
                fi
                current_rule="$line"
            fi
        fi
    done < "$RULES_FILE"
    
    # Don't forget the last rule
    if [[ -n "$current_signature" && -n "$current_rule" ]]; then
        EXISTING_RULES["$current_signature"]="$current_rule"
        EXISTING_RULES_COUNT=$((EXISTING_RULES_COUNT + 1))
    fi
}

# Function to generate a signature for a device
get_device_signature() {
    local vendor=$1
    local product=$2
    local serial=$3
    
    if [[ "$serial" != "UNKNOWN" ]]; then
        echo "${vendor}:${product}:${serial}"
    else
        echo "${vendor}:${product}"
    fi
}

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

# Read existing rules before processing
read_existing_rules

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
        
        # Compute signature early so we can check existing rules
        DEVICE_SIGNATURE=$(get_device_signature "$VENDOR" "$PRODUCT" "$SERIAL")
        
        # Check if this device already has a registered rule
        EXISTING_NAME=""
        IS_EXISTING=false
        if [[ -n "${EXISTING_RULES[$DEVICE_SIGNATURE]:-}" ]]; then
            EXISTING_RULE="${EXISTING_RULES[$DEVICE_SIGNATURE]}"
            if [[ $EXISTING_RULE =~ SYMLINK\+=\"([^\"]+)\" ]]; then
                EXISTING_NAME="${BASH_REMATCH[1]}"
                IS_EXISTING=true
            fi
        fi
        
        # Sanitize product name as fallback suggested name
        SUGGESTED_NAME=$(echo "$PRODUCT_NAME" | tr ' ' '_' | tr -cd 'a-zA-Z0-9_-' || echo "serial_device")
        if [[ -z "$SUGGESTED_NAME" ]]; then
            SUGGESTED_NAME="serial_device"
        fi
        if [[ "$SUGGESTED_NAME" == "serial_device" ]]; then
            SUGGESTED_NAME="${SUGGESTED_NAME}_${DEVICE_COUNT}"
        fi
        
        # Use existing name as default if registered, otherwise use suggested name
        if [[ "$IS_EXISTING" == true ]]; then
            DEVICE_NAME="$EXISTING_NAME"
        else
            DEVICE_NAME="$SUGGESTED_NAME"
        fi
        
        # Display device details
        echo "  Device Node:      $tty_device"
        echo "  Vendor ID:        $VENDOR"
        echo "  Product ID:       $PRODUCT"
        echo "  Serial Number:    $SERIAL"
        echo "  Manufacturer:     $MANUFACTURER"
        echo "  Product:          $PRODUCT_NAME"
        if [[ "$IS_EXISTING" == true ]]; then
            echo "  Registered Name:  /dev/$EXISTING_NAME  (already in udev rules)"
        else
            echo "  Suggested Name:   /dev/$SUGGESTED_NAME  (new device)"
        fi
        echo ""
        
        # Get device name from --name parameter if provided, otherwise prompt user
        if [[ "$INTERACTIVE" == true ]]; then
            if [[ "$IS_EXISTING" == true ]]; then
                read -p "Keep existing name [$EXISTING_NAME] or enter new name: " USER_INPUT
            else
                read -p "Confirm device name [$DEVICE_NAME] or enter alternative: " USER_INPUT
            fi
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
        
        # Track this signature as processed
        PROCESSED_SIGNATURES["$DEVICE_SIGNATURE"]=1
        
        # Track devices by signature for duplicate detection
        if [[ -z "${SIGNATURE_DEVICES[$DEVICE_SIGNATURE]:-}" ]]; then
            SIGNATURE_DEVICES["$DEVICE_SIGNATURE"]="$tty_device|$VENDOR|$PRODUCT|$PRODUCT_NAME"
        else
            # Append this device to the signature (indicates a duplicate)
            SIGNATURE_DEVICES["$DEVICE_SIGNATURE"]+="||$tty_device|$VENDOR|$PRODUCT|$PRODUCT_NAME"
        fi
        
        # Add rule to content
        RULES_CONTENT+=$'\n'"# Device: $PRODUCT_NAME ($tty_device)"
        RULES_CONTENT+=$'\n'"$RULE"
        RULES_CONTENT+=$'\n'""
        
        DEVICE_COUNT=$((DEVICE_COUNT + 1))
    fi
done

# Check for duplicate device signatures (identical devices without unique serials)
echo "Checking for duplicate device signatures..."
DUPLICATE_COUNT=0
for signature in "${!SIGNATURE_DEVICES[@]}"; do
    IFS='||' read -ra DEVICES <<< "${SIGNATURE_DEVICES[$signature]}"
    
    if [[ ${#DEVICES[@]} -gt 1 ]]; then
        DUPLICATE_COUNT=$((DUPLICATE_COUNT + 1))
        
        # Extract info from first device
        IFS='|' read -r tty vendor product product_name <<< "${DEVICES[0]}"
        
        # Check if this is a CP210X device (vendor 10c4)
        if [[ "$vendor" == "10c4" ]]; then
            WARNING="WARNING: $DUPLICATE_COUNT duplicate CP210X device(s) detected with signature: $signature"
            DUPLICATE_WARNINGS+=("$WARNING")
            DUPLICATE_WARNINGS_COUNT=$((DUPLICATE_WARNINGS_COUNT + 1))
        fi
    fi
done

# Add back any existing rules that weren't updated (devices not currently attached)
if [[ $EXISTING_RULES_COUNT -gt 0 ]]; then
    PRESERVED_COUNT=0
    for signature in "${!EXISTING_RULES[@]}"; do
        if [[ -z "${PROCESSED_SIGNATURES[$signature]:-}" ]]; then
            RULES_CONTENT+=$'\n'"# (Preserved - device not currently attached)"
            RULES_CONTENT+=$'\n'"${EXISTING_RULES[$signature]}"
            RULES_CONTENT+=$'\n'""
            PRESERVED_COUNT=$((PRESERVED_COUNT + 1))
        fi
    done
    
    if [[ $PRESERVED_COUNT -gt 0 ]]; then
        echo "Preserved $PRESERVED_COUNT existing rule(s) for devices not currently attached."
        echo ""
    fi
fi

if [[ $DEVICE_COUNT -eq 0 ]]; then
    echo "No USB serial devices found."
    if [[ $EXISTING_RULES_COUNT -gt 0 ]]; then
        echo "Existing rules have been preserved in $RULES_FILE."
    fi
    exit 0
fi

echo "=========================================="
echo "Generated udev rules ($DEVICE_COUNT device(s)):"
echo "=========================================="
echo "$RULES_CONTENT"
echo ""

# Display any duplicate device warnings
if [[ $DUPLICATE_WARNINGS_COUNT -gt 0 ]]; then
    echo "=========================================="
    echo "DUPLICATE DEVICE WARNING"
    echo "=========================================="
    for warning in "${DUPLICATE_WARNINGS[@]}"; do
        echo "$warning"
    done
    echo ""
    echo "These CP210X devices have identical parameters and will conflict in udev."
    echo "Consider reprogramming their serial numbers using cp210x-cfg:"
    echo ""
    echo "  https://github.com/DiUS/cp210x-cfg"
    echo ""
    echo "Example:"
    echo "  cp210x-cfg -l              # List devices"
    echo "  cp210x-cfg -d x.y          # Show device details where x.y is <bus>.<device>"
    echo "  cp210x-cfg -d x.y -S 0016  # Set unique serial"
    echo ""
    echo "To show details for all CP210X devices, run:"
    echo "  cp210x-cfg -l | awk 'match($0, /bus ([0-9]+), dev ([0-9]+)/, a) {system(\"echo ; ./cp210x-cfg -d \" a[1] \".\" a[2])}'; echo "
    echo ""
fi

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
