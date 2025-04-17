#!/bin/bash

# Navigate to the Documents directory
cd ~/Documents || {
  echo "Failed to switch to Documents directory."
  exit 1
}

# Activate the virtual environment
source venv/bin/activate || {
  echo "Failed to activate virtual environment 'venv'."
  exit 1
}

# Navigate to the uas_package directory
cd uas_package || {
  echo "Failed to switch to uas_package directory."
  exit 1
}

# Start the Python script
python uas_state_machine.py || {
  echo "Failed to run uas_state_machine.py."
  exit 1
}
