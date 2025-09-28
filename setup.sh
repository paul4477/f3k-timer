#!/bin/bash
#
#
echo Setup...

## create python venv
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

sudo setcap 'cap_net_bind_service=+ep cap_net_raw=+ep' .venv/bin/python

## Set Master audio control to full volume
amixer sset Master,0 "100%"
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
./prep.sh $ESPNOW_DEV $CHANNEL

python f3k_timer.py
EOL
