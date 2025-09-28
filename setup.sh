#!/bin/bash
#
#
echo Seting up Python venv. May take a moment...

fn_exists() {
  LC_ALL=C type $1 2>&1 | grep -q 'is a function'
}

## Check if we are in a venv already and deactivate it
if ( fn_exists deactivate )
then
	deactivate
fi

## create python venv
python -m venv .venv
source .venv/bin/activate
echo
echo Installing required modules...
echo
.venv/bin/pip install -r requirements.txt

echo
echo
echo Setting network capabilites for ESPNow access...
echo
sudo setcap 'cap_net_bind_service=+ep cap_net_raw=+ep' `readlink -f .venv/bin/python`
sudo getcap `readlink -f .venv/bin/python`
echo
echo Setting Master volume...
echo
## Set Master audio control to full volume
amixer sset Master,0 "100%"
echo
echo Creating start.sh
DIR=`pwd`
cat >start.sh <<EOL
#!/bin/bash
#
#
#
ESPNOW_DEV=wlan1
CHANNEL=4

cd $DIR
source .venv/bin/activate
sudo ifconfig \$ESPNOW_DEV down
sudo iwconfig \$ESPNOW_DEV mode monitor
sudo ifconfig \$ESPNOW_DEV up
sudo iwconfig \$ESPNOW_DEV channel \$CHANNEL

.venv/bin/python f3k_timer.py
EOL
chmod u+x start.sh
echo
echo Done.
echo
