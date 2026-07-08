import argparse
import json
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=str)
    parser.add_argument("--agent-id", type=str)
    parser.add_argument("--task-id", type=str)
    parser.add_argument("--max-turns", type=int, default=10)
    args, unknown = parser.parse_known_args()

    # Simulate doing work
    print(f"[{args.agent_id}] running task {args.task_id}")
    time.sleep(1)

    # Output JSON envelope as last line
    envelope = {
        "task_id": args.task_id,
        "ok": True,
        "output": f"Mock output for {args.prompt[:20]}",
        "tokens_in": len(args.prompt) // 4 if args.prompt else 0,
        "tokens_out": 42
    }
    print(json.dumps(envelope))

if __name__ == "__main__":
    main()
