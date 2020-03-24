#!/bin/sh

sudo cp mtb_barahl0bot /etc/init.d
sudo chmod +x /etc/init.d/mtb_barahl0bot
sudo update-rc.d mtb_barahl0bot defaults
