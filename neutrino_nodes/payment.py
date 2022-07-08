import pywaves as pw
import datetime as dt

pw.setNode('http://localhost:6869', chain='mainnet')
myAddress = pw.Address(privateKey='your_node_private_key')
dappAddress = '3P9vKqQKjUdmpXAfiWau8krREYAY1Xr69pE'
beneficiaryAddress = '3P_your_beneficiary_address'
fee = pw.DEFAULT_INVOKE_SCRIPT_FEE
amount = myAddress.balance() - fee

if result > 0:
    result = myAddress.invokeScript(dappAddress, 'distributeMinerReward', params=[{"type": "string", "value": beneficiaryAddress}], payments=[{"assetId": None, "amount": amount}], feeAsset = None, txFee=fee)
else:
    result = "Not enough balance."
    
now = dt.datetime.now()
print(now.strftime("%Y-%m-%d %H:%M:%S"))
print(result)
