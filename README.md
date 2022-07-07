# neutrino-utilities

## Payout script in python
System preparation:
```
sudo apt install build-essential
sudo apt install python3-dev
sudo apt install python3-pip
sudo apt install python3-testresources
pip install pywaves
```

You must allow your node REST API at least for localhost:
```
  # Node's REST API settings
  rest-api {
    # Enable/disable node's REST API
    enable = yes

    # Network address to bind to
    bind-address = "127.0.0.1"
```
Edit the script - insert your node private key and your beneficiary address (where the 5% of rewards will be sent)

Test the script:
```
python3 payment.py
```
Now, edit the crontab to run this script periodically:
```
crontab -e
```
Add this line to execute payout script twice a day at 01:00 and 13:00 (choose your own times), also correct the paths:
```
0 1,13 * * * python3 /home/your_dir/payment.py >> /home/your_dir/payment.log 2>&1
```
## Node monitoring scripts in python
System preparation:
```
pip install pyTelegramBotAPI
```
You must allow your node REST API at least for localhost. 
Script height.py determines height of the blocks and send it via ftp to your webhost.
Edit the script - insert your hostname, user and password (line 11 of the height.py).
Test the script:
```
python3 height.py
```
Check existance of height.txt in the same dir as height.py and http://hostname/height.txt wth the latest blocks height.
Add this line to execute payout script every minute, also correct the paths:
```
*/1 * * * * python3 /home/your_dir/height.py >> /home/your_dir/height.log 2>&1
```
Script telegram_bot.py checks once per minute http://hostname/height.txt and compares blocks height of your Node with reference height. You'll get alert in case |reference height - node height| >= 3 . This script should not be run on the same vps where your node runs.
Edit the script telegram_bot.py - insert height_url (http://hostname/height.txt) and token (find in Telegram @BotFather and use command /newbot)
Test the script:
```
python3 telegram_bot.py
```

## Install a RIDE script to mining node and invoke the constructor
As you know, since node version 1.4 it is possible for mining node to have a script.


System preparation:
```
sudo apt install build-essential
sudo apt install python3-dev
sudo apt install python3-pip
sudo apt install python3-testresources
pip install pywaves
```

Either allow your node REST API for localhost:
```
  # Node's REST API settings
  rest-api {
    # Enable/disable node's REST API
    enable = yes

    # Network address to bind to
    bind-address = "127.0.0.1"
```
or change node url in the python script to any public node, e.g.
```
pw.setNode('https://nodes.wavesnodes.com', chain='mainnet')
```
Edit the script - insert your node private key and actual base64-encoded script instead of script = 'base64:...' line. Edit your beneficiary address (where the 5% of rewards will be sent).
Run the script.

NOTES:
* source file in RIDE is passed via pipe
* there is 30 sec delay between setting the script and calling the constructor, make sure there are no errors
```
curl https://raw.githubusercontent.com/waves-exchange/neutrino-contract/master/script/generator.ride | python3 set_script.py
```
