---
id: hermes
role: delegate
adapter: http
endpoint: http://127.0.0.1:8001/run
cost_defaults: { max_turns: 20, max_tokens: 50000 }
bindings: []
capabilities: [research, summarize, knowledge_lookup]
---
# hermes
Research + knowledge delegate. Reached only via delegate_task.

