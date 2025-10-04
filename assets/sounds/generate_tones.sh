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

if [ ! -d venv-tone_gen ]; 
then
  echo It seems like you may not have a venv set up.
  echo Generating...
  python -m venv venv-tone_gen
  if [ -d venv-tone_gen/bin ];
  then
    BIN_DIR=venv-tone_gen/bin
  else
    BIN_DIR=venv-tone_gen/Scripts
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
