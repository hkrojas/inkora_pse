import subprocess
import json

p = subprocess.Popen(['notebooklm-mcp'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# Send initialize
p.stdin.write(json.dumps({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0'}
    }
}) + '\n')
p.stdin.flush()

# Read until we get initialize response
while True:
    line = p.stdout.readline()
    if not line: break
    try:
        resp = json.loads(line)
        if resp.get('id') == 1:
            break
    except Exception as e:
        pass

p.stdin.write(json.dumps({
    'jsonrpc': '2.0',
    'method': 'notifications/initialized'
}) + '\n')
p.stdin.flush()

# Request tools
p.stdin.write(json.dumps({
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'tools/list',
    'params': {}
}) + '\n')
p.stdin.flush()

# Read until we get tools response
while True:
    line = p.stdout.readline()
    if not line: break
    try:
        resp = json.loads(line)
        if resp.get('id') == 2:
            tools = resp.get('result', {}).get('tools', [])
            print(f'Total tools: {len(tools)}')
            names = [t.get('name') for t in tools]
            for n in names:
                print(f'- {n}')
            for t in tools:
                name = t.get('name', '')
                if 'notebook' in name.lower() and 'create' in name.lower():
                    print(f'Create notebook tool EXACT name: {name}')
            break
    except Exception as e:
        pass

# Test call to list notebooks
p.stdin.write(json.dumps({
    'jsonrpc': '2.0',
    'id': 3,
    'method': 'tools/call',
    'params': {
        'name': 'list_notebooks',
        'arguments': {}
    }
}) + '\n')
p.stdin.flush()

while True:
    line = p.stdout.readline()
    if not line: break
    try:
        resp = json.loads(line)
        if resp.get('id') == 3:
            print("Test call (list_notebooks) output:")
            print(json.dumps(resp.get('result', {}), indent=2))
            break
    except Exception as e:
        pass
