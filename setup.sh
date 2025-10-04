#!/bin/bash
#
#
echo Seting up Python venv. May take a moment...

fn_exists() {
  LC_ALL=C type $1 2>&1 | grep -q 'is a function'
}

## Check if we are in a venv already and deactivate it
## to avoid confusion.
if ( fn_exists deactivate )
then
	deactivate
fi

venv_name=venv-f3k-timer
default_voice=en_US-lessac-medium

## create python venv
python -m venv $venv_name

if [ -d $venv_name/bin ];
then
  BIN_DIR=$venv_name/bin # Linux
else
  BIN_DIR=$venv_name/Scripts # Windows
fi
echo
echo Updating Pip...
echo
$BIN_DIR/pip install --upgrade pip
echo
echo Installing required modules...
echo
$BIN_DIR/pip install -r requirements.txt
echo
echo Downloading voice data: 
$BIN_DIR/python -m piper.download_voices en_US-lessac-medium
echo
cd assets/sounds/

## Run tone generation. Includes setting up own venv
source generate_tones.sh
## Run speach generation (uses main venv where Piper is installed.)
../../$BIN_DIR/python generate_language.py
cd -

echo
echo
echo Setting network capabilites for ESPNow access...
echo
sudo setcap 'cap_net_bind_service=+ep cap_net_raw=+ep' `readlink -f $BIN_DIR/python`
sudo getcap `readlink -f $BIN_DIR/bin/python`
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

$venv_name/bin/python f3k_timer.py
EOL
chmod u+x start.sh
echo
echo Done.
echo

### Add systemd service