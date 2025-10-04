#!/bin/bash
set -e

fn_exists() {
  LC_ALL=C type $1 2>&1 | grep -q 'is a function'
}

## Check if we are in a venv already and deactivate it
if ( fn_exists deactivate )
then
	deactivate
fi

venv_name=venv-tone_gen

if [ ! -d $venv_name ]; 
then
  echo It seems like you may not have a venv set up.
  echo Generating...
  python -m venv $venv_name
  if [ -d $venv_name/bin ];
  then
    BIN_DIR=$venv_name/bin
  else
    BIN_DIR=$venv_name/Scripts
  fi
  echo
  echo Upgrading Pip...
  echo
  $BIN_DIR/pip install --upgrade pip
  echo
  echo Installing required libraries...
  echo
  $BIN_DIR/pip install -r requirements_tone_gen.txt
fi
$BIN_DIR/python generate_tones.py "$@"

echo
echo If tone generation was successful you could 
echo save space by removing:
echo `pwd`"/$venv_name"
echo
