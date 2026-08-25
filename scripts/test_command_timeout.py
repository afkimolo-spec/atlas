from pathlib import Path

from atlas.tools import CommandExecutor


ROOT = Path(
    "/home/administrator/workspace/atlas"
)

executor = CommandExecutor(
    ROOT,
    default_timeout=1.0,
)

print("=" * 60)
print("COMMAND TIMEOUT")
print("=" * 60)

result = executor.run(
    "sleep 5",
    timeout=0.5,
)

print("Timed out  :", result.timed_out)
print("Return code:", result.return_code)
print("Duration   :", f"{result.duration:.4f}s")

assert result.timed_out
assert result.return_code == -1

print("=" * 60)
print("Command timeout verified.")
print("=" * 60)
