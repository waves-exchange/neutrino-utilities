import pywaves as pw
import base64

pw.setNode('http://localhost:6869', chain='mainnet')
myAddress = pw.Address(privateKey='my_node_private_key')
fee = pw.DEFAULT_SCRIPT_FEE
script = 'base64:'
scriptSource = base64.b64decode(script)
result = myAddress.setScript(scriptSource, txFee=fee, timestamp=0)

print(result)
