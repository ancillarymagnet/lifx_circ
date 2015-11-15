# lifx_circ
Circadian-tuned LIFX control daemon

This tool is meant to provide simple circadian LUT behavior for your LIFX lights.

I've included a sample LUT intended to mimic the color temperature of sunlight, but any LUT is possible.

Lat/Long settings are used to allow Pyephem to extract and localize timing of events named 'sunrise', 'noon', and 'sunset' on a daily basis.

If you enable the 'extended-sunlight-mode' flag, those events will be localized based on their timings during the Summer solstice. - I leave that feature on as I enjoy the 'SAD'-fighting effects of extended blue light during the short Winter days.


You'll need to put your LIFX HTTP API token into the user_data.json 'token' field ... there's a dummy in there for now.
You can generate that token for your account here: https://cloud.lifx.com/settings


This is still WIP but I'm hacking on it.

