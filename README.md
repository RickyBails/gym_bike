# gym_bike
Script for collecting HRM and power data from bluetooth devices and sending to Splunk

# Part 1: setting up the python collection script

The python script in this repo runs continuously, connecting to one pair of favero assioma power meter pedals and multiple heart rate monitors, collects per-second stats and sends them to both and O11y cloud instance and an HTTP event collector as splunk events.

## Pre-requisites
Python needs to be 3.3 or higher for venv to work

## 1) Clone the repository
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

## 2) Create a virtual environment
python3 -m venv venv

source venv/bin/activate

## 3) Install dependencies
pip install -r requirements.txt

## 4) Configure
vi gym_collect.json

- review if any of the settings need changing - have the core/O!1y endpoints change or the HRMs and power pedals?
- replace the heart rate monitor ID with the IDs of all the heart rate monitors being used
   (to find the IDs of the HRMs, put them on and run the script with 'python gym_collect.py' and the script starts by scanning all nearby BT devices and printing name and ID to stdout) 
- replace the power pedals ID with the ID of the power pedals being used (have to be favero assioma)
- replace the O11Y* variables with the URL/token of the O11y cloud instance you want to send to, if needed
- replace the HEV variables with the HEC endpoint on the core instance you want to send events to.

## 5) Run the script
python gym_collect.py

(It should connect to all HRMs and power pedals listed in the config file and send per-second data to both O11y cloud and the core platform)

# Part 2: Setting up Splunk Platform

Check Metrics index gym_events exists, if not create it with defaults (event-type index)

Configure a HEC token for events data
- Name: gym_bike
- Default Index: gym_events (create new)
- Sourcetype: gym_bike (new, custom)

N.B. for a new instance, your HEC may be created disabled, and you need to enable in global settings (button on HEC config page)


# Part 3: Setting up the pedals for an event

## Pre-requisites

- a stationary exercise bike where you can change the pedals, ideally one with saddle and handlebar adjustment to fit different people. Needs to provide some resistance so you can generate power but NOT using air resistance (e.g. concept 2)  - you want it to be quite when pedalling so you can have a conversation
- The favero assioma power meter pedals, in a box with a charging lead and 4 pedal washers in a bag
- (nice-to-have) a large fan aimed at the top half of the ride on the bike
- a mac laptop. The OS you're using needs direct access to the bluetooth controller. most windows VM envs don't allow this but on macs it's standard. The python script was developed and tested on macs
- a ruler or tape measure (for measuring the crank length of the bike) unless the crank length is already printed on the cranks, or you otherwise know what it is.
- an 8mm allen key (for fitting pedals) and MAYBE a 15mm pedal spanner for removing old pedals if they do not have 8mm socket.
- install the 'favero assioma' app on your phone.
- a table next to the exercise bike to put the mac on, ideally so you can reach it from the bike
- the ability to pedal on the bike for long periods of time while having a conversation. Ideally you are relatively fit and familiar with pedalling a bike.

## Event set-up

- launch the 'favero assioma' app and connect with the pedals. Take the pedals out of 'travel mode' which they should be in if coming from storage
- measure/obtain the crank length of the bike and input this (in mm) into the app. It's likely to be 165mm, 170mm or 175mm.
- charge the pedals, using the clip-on usb lead in the box
- remove any existing pedals on the exercise bike. Use 8mm allen key or a 15mm pedal wrench
- fit the favero assioma power pedals. Start with the LHS one (the only one measuring power and place enough washers on the pedal spindle so that the bulbous part of the pedal spindle (the bit the charger attaches to) does not rub on the cranks when the pedals are rotated. Note that on bikes, the LH pedals and cranks have a reverse thread. Rather than 'righty-tighty lefty loosy' rule, use this: to loosen pedals, rotate the spindles as the bike wheels would rotate when reversing, and to tighten/fit pedals, rotate pedal spindle as wheels turn going forward.
- in the splunk platform hosting the HEC and dashboard, launch the exercise_bike_2025_v1 dashboard in the 'Exercise Bike' and...
  - click on the cog icon above the 'Rider HRM Device' on the top edge, and check the list includes the name/id of all the bluetooth HRMs you are using. When configuring a new HRM, get the name/id by putting it on and running the python script: all BT devices visible to the mac are listed
  - click on the cog icon above the 'Rider' dropdown at the top of the dashboard and check it lists all the riders that will be using the bike. Enter name and max heart rate (if they don't know, use 220-age)

## Event tear-down

- launch the 'favero assioma' phone app and put the pedals in travel mode. This stops the battery running down between events
- remove pedals and place any washers used back in the bag in the box - there are 4 washers in total
