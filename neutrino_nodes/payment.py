import pywaves as pw
import datetime as dt

pw.setNode('http://localhost:6869', chain='mainnet')
myAddress = pw.Address(privateKey='your_node_private_key')
dappAddress = '3P9vKqQKjUdmpXAfiWau8krREYAY1Xr69pE'
beneficiaryAddress = '3P_your_beneficiary_address'
fee = pw.DEFAULT_INVOKE_SCRIPT_FEE

amount = myAddress.balance() - fee

if amount > 2400000000:

 result = myAddress.invokeScript(dappAddress, 'distributeMinerReward',
params=[{"type": "string", "value": beneficiaryAddress}],
payments=[{"assetId": None, "amount": 2400000000}], # fixed amount of 24 waves - short term
feeAsset = None, txFee=fee)

else:
    result = "Not generated reward of 24 waves to do invoke - distributeMinerReward. Current balance of Waves: " + str(amount / 100000000)

now = dt.datetime.now()
print(now.strftime("%Y-%m-%d %H:%M:%S"))
print(result)
