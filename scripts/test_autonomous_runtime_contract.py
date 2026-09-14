from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from atlas.runtime.autonomous import AutonomousRuntime


class FakeDeveloper:
    def next_action(
        self,
        task: str,
        *,
        session_id: str,
        state: str,
    ) -> dict[str, str]:
        return {
            "action": "finish",
            "summary": "Contract verification completed.",
        }


print("=" * 60)
print("ATLAS AUTONOMOUS RUNTIME CONTRACT")
print("=" * 60)

with TemporaryDirectory() as directory:
    workspace = Path(directory)

    runtime = AutonomousRuntime(
        workspace=workspace,
        developer=FakeDeveloper(),
        verification_command="true",
        max_steps=5,
    )

    assert runtime.status == "created"
    print("Initial status             : PASS")

    result = runtime.execute(
        "Verify autonomous runtime contract.",
        session_id="runtime-contract",
    )

    assert result.status == "completed"
    assert runtime.status == "completed"
    assert result.succeeded

    print("Execution result status    : PASS")
    print("Runtime status             : PASS")
    print("Success contract           : PASS")

print("=" * 60)
print("AUTONOMOUS RUNTIME CONTRACT: VERIFIED")
print("=" * 60)
