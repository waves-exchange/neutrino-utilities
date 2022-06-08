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
