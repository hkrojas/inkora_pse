import subprocess
import json
import sys

p = subprocess.Popen(['notebooklm-mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def send(msg):
    p.stdin.write(json.dumps(msg) + '\n')
    p.stdin.flush()

def read_id(expected_id):
    while True:
        line = p.stdout.readline()
        if not line: return None
        try:
            r = json.loads(line)
            if r.get('id') == expected_id:
                return r
        except Exception:
            pass

# Initialize
send({
    'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05', 'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0'}
    }
})
read_id(1)
send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

# Get tools
send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}})
r2 = read_id(2)
tools = r2.get('result', {}).get('tools', [])
print(f"Total tools: {len(tools)}")
print("Tool names:", [t.get('name') for t in tools])

send({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'notebook_list', 'arguments': {}}})
r3 = read_id(3)
print("Test call (notebook_list) output:")
if r3:
    print(json.dumps(r3.get('result', {}), indent=2))
else:
    print("NO RESPONSE")
