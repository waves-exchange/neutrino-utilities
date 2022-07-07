import pywaves as pw
import time
import sys

pw.setNode('http://localhost:6869', chain='mainnet')
myAddress = pw.Address(privateKey='my_node_private_key')
beneficiaryAddressStr58 = '3P_your_beneficiary_address'
setFee = 3 * pw.DEFAULT_SCRIPT_FEE # current compiled script size is 2008 bytes, which is rounded to 3k and results in 0.003 fee
scriptSource = sys.stdin.read()
result = myAddress.setScript(scriptSource, txFee=setFee)
print(result)

print('Waiting for transaction to finalize...')
time.sleep(30)

callFee = pw.DEFAULT_INVOKE_SCRIPT_FEE
result = myAddress.invokeScript(myAddress.address, 'constructor', params=[{"type": "string", "value": beneficiaryAddressStr58}], payments=[], feeAsset =
None, txFee=callFee)
print(result)

