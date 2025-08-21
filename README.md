# gym_bike
Script for collecting HRM and power data from bluetooth devices and sending to Splunk

# Pre-requisites
Python needs to be 3.3 or higher for venv to work

# 1) Clone the repository
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# 2) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure
vi gym_collect.json

review if any of the settings need changing - have the core/O!1y endpoints change or the HRMs and power pedals?
replace the heart rate monitor ID with the IDs of all the heart rate monitors being used
  (to find the IDs of the HRMs, put them on and run the script with 'python gym_collect.py'
     - it starts by scanning all nearby BT devices and printing name and ID to stdout)
replace the power pedals ID with the ID of the power pedals being used (have to be favero assioma)
replace the O11Y* variables with the URL/token of the O11y cloud instance you want to send to, if needed
replace the HEV variables with the HEC endpoint on the core instance you want to send events to.

# 5) Run the script
python gym_collect.py

It should connect to all HRMs and power pedals and send per-second data to both O11y cloud and the core platform
