from pathlib import Path

from atlas.tools import CommandExecutor


ROOT = Path(
    "/home/administrator/workspace/atlas"
)


executor = CommandExecutor(
    ROOT
)

print("=" * 60)
print("ATLAS COMMAND EXECUTOR")
print("=" * 60)

print("Workspace :", executor.workspace)

# ------------------------------------------------------------
# Basic command
# ------------------------------------------------------------

result = executor.run(
    "printf 'Command executor operational.'"
)

print("-" * 60)
print("BASIC COMMAND")
print("-" * 60)

print("Return code :", result.return_code)
print("Output      :", result.stdout)
print("Succeeded   :", result.succeeded)
print("Duration    :", f"{result.duration:.4f}s")

assert result.succeeded

assert (
    result.stdout.strip()
    == "Command executor operational."
)

# ------------------------------------------------------------
# Working directory
# ------------------------------------------------------------

result = executor.run(
    "pwd"
)

print("-" * 60)
print("WORKING DIRECTORY")
print("-" * 60)

print("Output :", result.stdout.strip())

assert result.succeeded
assert (
    Path(result.stdout.strip()).resolve()
    == ROOT
)

# ------------------------------------------------------------
# Repository command
# ------------------------------------------------------------

result = executor.run(
    "git branch --show-current"
)

print("-" * 60)
print("GIT")
print("-" * 60)

print(
    "Branch :",
    result.stdout.strip(),
)

assert result.succeeded

# ------------------------------------------------------------
# Relative working directory
# ------------------------------------------------------------

result = executor.run(
    "pwd",
    cwd="src",
)

print("-" * 60)
print("RELATIVE CWD")
print("-" * 60)

print("Output :", result.stdout.strip())

assert result.succeeded

assert (
    Path(result.stdout.strip()).resolve()
    == ROOT / "src"
)

# ------------------------------------------------------------
# Failed command
# ------------------------------------------------------------

result = executor.run(
    "sh -c 'printf failure >&2; exit 7'"
)

print("-" * 60)
print("FAILURE HANDLING")
print("-" * 60)

print("Return code :", result.return_code)
print("stderr      :", result.stderr.strip())
print("Succeeded   :", result.succeeded)
print("Failed      :", result.failed)

assert result.failed
assert result.return_code == 7
assert "failure" in result.stderr

# ------------------------------------------------------------
# Workspace containment
# ------------------------------------------------------------

print("-" * 60)
print("WORKSPACE SECURITY")
print("-" * 60)

try:
    executor.run(
        "pwd",
        cwd="/tmp",
    )

except PermissionError:
    print(
        "Outside-workspace execution blocked."
    )

else:
    raise AssertionError(
        "Workspace escape was not blocked."
    )

print("=" * 60)
print("Command executor verified.")
print("=" * 60)
