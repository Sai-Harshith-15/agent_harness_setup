# Contract: Data Loss Prevention (DLP)

The DLP subsystem (Phase 2.12) enforces safe data handling by preventing sensitive credentials and high-entropy strings from leaking into persistent storage (Obsidian / SQLite) or network logs.

## 1. Pattern Matching
The `DLPFilter` is responsible for scrubbing text using regular expressions. The following patterns are mandatory:
- **AWS Keys**: `AKIA[0-9A-Z]{16}` -> `[REDACTED_AWS_KEY]`
- **Bearer Tokens**: `Bearer\s+[A-Za-z0-9\-\._~\+\/]+` -> `Bearer [REDACTED_TOKEN]`
- **GitHub PATs**: `ghp_[0-9a-zA-Z]{36}` -> `[REDACTED_GITHUB_PAT]`
- **Slack Tokens**: `xox[baprs]-[0-9a-zA-Z\-]+` -> `[REDACTED_SLACK_TOKEN]`
- **Private Keys**: `-----BEGIN PRIVATE KEY-----...` -> `[REDACTED_PRIVATE_KEY]`
- **High Entropy (Gap 3.2)**: `\b[0-9a-zA-Z]{40,}\b` -> `[REDACTED_HIGH_ENTROPY]`

## 2. Hit Policies
Administrators can configure the `DLP_HIT_POLICY` in the environment to dictate how the system reacts to a pattern match:
- `redact` (default): Replaces the matched substring with a placeholder and allows the request to continue.
- `block`: Immediately aborts the operation and raises a `403 Forbidden` HTTP exception.
- `quarantine`: Returns a `202 Accepted` but diverts the payload to a quarantine table for human review.

## 3. Scope
All inbound text for `append_implement`, `log_decision`, and arbitrary vault edits must pass through the `DLPFilter.scrub()` pipeline before reaching the Obsidian backend or control plane databases.
