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


if [ -d venv-tone_gen ]; 
then
  if [ -d venv-tone_gen/bin ];
  then
    source venv-tone_gen/bin/activate
  else
    source venv-tone_gen/Scripts/activate
  fi
  python generate_tones.py "$@"
  deactivate
else
  echo It seems like you may not have a venv set up.
  echo Generating...
  python -m venv venv-tone_gen
  if [ -d venv-tone_gen/bin ];
  then
    source venv-tone_gen/bin/activate
  else
    source venv-tone_gen/Scripts/activate
  fi
  pip install -r requirements_tone_gen.txt
  deactivate
fi