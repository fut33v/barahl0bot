# barahl0bot

Telegram bot and VKontakte albums parser, which gets new photos from given VK albums and posting it to telegram. 
Used for albums with photos of pre-owned bicycles for sale.

Tokens and other settings should be in ```settings.json``` (example in ```settings_example.json```)

Also in folder ```data``` stored file ```albums``` with parsed VK albums, file ```hash``` 
with pictures hash.

Works here: https://t.me/barahlochannel

## Dependencies

Dependencies are in requirements.txt

Install libpq-dev for psycopg2:

````
sudo apt-get install libpq-dev
````
