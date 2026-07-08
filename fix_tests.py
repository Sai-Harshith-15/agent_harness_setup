import os
import re
from context_server.app.identity import sign_identity

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    def replacer(match):
        agent_task = match.group(1)
        # If it's already signed (has 2 colons), skip it
        if agent_task.count(':') == 2:
            return match.group(0)
            
        agent, task = agent_task.split(':')
        signed = sign_identity(agent, task)
        return f'"X-Agent-Identity": "{signed}"'

    new_content = re.sub(r'"X-Agent-Identity":\s*"([^"]+)"', replacer, content)
        
    with open(filepath, 'w') as f:
        f.write(new_content)

test_files = [
    'context_server/tests/test_phase5.py',
    'context_server/tests/test_phase3.py',
    'context_server/tests/test_main.py',
    'context_server/tests/test_phase6.py',
    'context_server/tests/test_phase7.py',
    'context_server/tests/test_phase8.py'
]

for tf in test_files:
    process_file(tf)
print('Done fixing tests!')
