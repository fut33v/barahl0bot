#!/bin/sh

sudo cp barahl0bot /etc/init.d
sudo chmod +x /etc/init.d/barahl0bot
sudo update-rc.d barahl0bot defaults
