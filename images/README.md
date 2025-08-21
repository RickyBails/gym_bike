# Image files for Splunk Dashboards

These are all the images used by the exercise bike dashboard. They are recorded because they do not get exported when an app is saved, and the exercise bike app is one that might get moved around to different splunk core instances.

WhatDashboardShouldLookLike.png This is a screenshot of the finished product to be used as a guide (not for uploading into splunk)

There are 2 types of image here. The png files are for 'image' type objects created from the 'add image' menu. The svg files are for icons. The two types are updated in different ways, described below

# Icons

The two icons can be uploaded as follows:
1) in edit mode, click th 'add icon' menu (2x2 squares) and at the bottom of the pop-up click 'upload file'. This will add the file to the KV store and place a large version in the middle of the dashboard.
2) click on the icon created and go to the code view
3) view the source code and copy the value of the "icon" field/value pair. It'll look something like: splunk-enterprise-kvstore://68a78e7974a56d66df076991
4) now select the blacked-out icon where you want the image to go, find the source code and paste the value you just copied over the top
5) delete the new icon that was created when you uploaded the image. You don't need that, you need the image in the kvstore.
   
settings_black_and_white_22447.svg This is the cog icon used twice at the top of the dashboard - one above the 'Rider HRM Device' dropdown and one above the 'Rider' dropdown. Both are links to the lookup editing page for the relevant configs that drive the dropdown

heart_rate_icon.svg  -  This is the little red heart to the right of the 'rider' dropdown. Doesn't need to be the single value icon that it is

# Images

sram_xplr_cranks.png  - This is the big crankset image that dominates the dashboard. Select this large image on the dashboard in edit mode and in the configuration panel on the RHS, go to the Image Content section, and upload the image file there.

watts_text.png - This overwrites the 'sram' logo on the cranks. select the transparent image bordering the larger 'sram' logo on the crank arm and replace image as above

heart_brighter.png - this is the red heart background for the heart rate single value. click the larger of the two widgets above/right of the chainwheel and upload the image (the inner widget is the value).
