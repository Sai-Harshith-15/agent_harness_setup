# Contract: Sandbox Driver

The `SandboxDriver` provides isolation for running registered agents. 
The system defines this swappable interface rather than hardcoding a cloud execution environment.

## Interface Methods
- `spawn(bounds) -> id`: Starts a new sandbox with the given resource boundaries, returning its unique identifier.
- `exec(id, cmd) -> result`: Executes a command in the sandbox and returns its standard output/error/code.
- `terminate(id)`: Forcefully shuts down the sandbox and frees resources.
- `snapshot(id) -> path`: Captures the file system and runtime state of the sandbox to a path on the host, for later resume or forensic analysis.

## Implementations
- `LocalRunner`: The default on this host. A containerized local execution environment (e.g., Windows Sandbox / WSL2_FIRECRACKER equivalent) designed for a zero-cloud dev loop.
- `E2BRunner`: The documented cloud target, enabled by configuration, when running remotely or in hybrid configurations.
