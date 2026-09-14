from __future__ import annotations

import json
from json import JSONDecoder
from typing import Any

from atlas.agents.base import BaseAgent


class DeveloperAgent(BaseAgent):
    """
    Autonomous engineering developer agent.

    The model proposes exactly one controlled engineering action at a time.

    The autonomous control loop is isolated from conversational history.
    Execution state is supplied explicitly by EngineeringExecutor and is
    bounded before being sent to the model.

    Actual filesystem, command, git, workspace, and security enforcement
    remains in Atlas's tool/security layer.
    """

    ACTION_TYPES = frozenset(
        {
            "read_file",
            "write_file",
            "run_command",
            "git_diff",
            "finish",
        }
    )

    MAX_TASK_CHARS = 8000
    MAX_STATE_CHARS = 5000
    MODEL_MAX_TOKENS = 512

    def __init__(self) -> None:
        super().__init__(
            role="developer",
            prompt_file="system.md",
            model="engineering",
        )

    @staticmethod
    def _tail(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value

        return (
            "[...earlier content truncated...]\n"
            + value[-limit:]
        )

    def next_action(
        self,
        task: str,
        *,
        session_id: str,
        state: str,
    ) -> dict[str, Any]:
        """
        Request exactly one structured engineering action.

        Internal autonomous control requests do not use conversational
        history, preventing recursive context growth during multi-step
        engineering execution.
        """

        if not isinstance(task, str) or not task.strip():
            raise ValueError(
                "task must be a non-empty string"
            )

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError(
                "session_id must be a non-empty string"
            )

        if not isinstance(state, str):
            raise TypeError(
                "state must be a string"
            )

        bounded_task = self._tail(
            task.strip(),
            self.MAX_TASK_CHARS,
        )

        bounded_state = self._tail(
            state,
            self.MAX_STATE_CHARS,
        )

        instruction = f"""
You are Atlas's autonomous engineering developer.

Your job is to perform ONE engineering action per request.

ENGINEERING TASK:
{bounded_task}

CURRENT EXECUTION STATE:
{bounded_state}

Return ONLY one JSON object.

Supported action types:

1. Read a file:
{{
  "type": "read_file",
  "path": "relative/path/to/file"
}}

2. Write a file:
{{
  "type": "write_file",
  "path": "relative/path/to/file",
  "content": "complete file contents"
}}

3. Run a command:
{{
  "type": "run_command",
  "command": "safe engineering command"
}}

4. Inspect git changes:
{{
  "type": "git_diff"
}}

5. Finish the task:
{{
  "type": "finish",
  "summary": "verified description of completed work"
}}

Rules:
- Return exactly ONE JSON object.
- The first JSON object is the only action Atlas will execute.
- Do not return an array.
- Do not return multiple actions.
- Do not wrap JSON in Markdown.
- Do not include explanatory prose before or after the JSON.
- Never use absolute filesystem paths.
- Never request network access.
- Never request git commit.
- Never bypass Atlas security controls.
- Prefer reading a file before replacing it when existing contents
  are required to preserve unrelated functionality.
- Run tests after modifications.
- Do not claim completion until verification has succeeded.
- For write_file, provide the COMPLETE intended file contents.
- For run_command, provide exactly one command.
- Use finish only when the task is actually complete and verified.
"""

        response = self.run(
            instruction,
            session_id=session_id,
            knowledge_query=bounded_task,
            include_history=False,
            persist_history=False,
            temperature=0.0,
            max_tokens=self.MODEL_MAX_TOKENS,
        )

        action = self._parse_action(response)
        return self._validate_action(action)

    @classmethod
    def _parse_action(
        cls,
        response: str,
    ) -> dict[str, Any]:
        """
        Extract the first valid JSON object from model output.
        """

        if not isinstance(response, str):
            raise TypeError(
                "Developer agent response must be a string."
            )

        text = response.strip()

        if not text:
            raise ValueError(
                "Developer agent returned an empty response."
            )

        # ------------------------------------------------------------
        # Remove markdown fences if the model ignored the JSON-only rule.
        # ------------------------------------------------------------
        if text.startswith("```"):
            lines = text.splitlines()

            if (
                lines
                and lines[0].strip().startswith("```")
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        decoder = JSONDecoder()

        # ------------------------------------------------------------
        # Exact JSON object.
        # ------------------------------------------------------------
        try:
            value, _ = decoder.raw_decode(text)

            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

        # ------------------------------------------------------------
        # JSON object embedded in surrounding model output.
        # ------------------------------------------------------------
        for index, character in enumerate(text):
            if character != "{":
                continue

            try:
                value, _ = decoder.raw_decode(
                    text[index:]
                )
            except json.JSONDecodeError:
                continue

            if isinstance(value, dict):
                return value

        raise ValueError(
            "Developer agent returned no valid JSON action. "
            f"Response: {self._tail(text, 4000)}"
        )

    @classmethod
    def _validate_action(
        cls,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate the developer action contract expected by EngineeringExecutor.

        Security-sensitive path and command authorization is delegated to
        Atlas's SecurityService and tool layer.
        """

        if not isinstance(action, dict):
            raise ValueError(
                "Developer action must be a JSON object."
            )

        action_type = action.get(
            "type"
        )

        if (
            not isinstance(action_type, str)
            or action_type not in cls.ACTION_TYPES
        ):
            raise ValueError(
                "Unsupported developer action type: "
                f"{action_type!r}"
            )

        normalized: dict[str, Any] = {
            "type": action_type,
        }

        # ------------------------------------------------------------
        # read_file / write_file
        # ------------------------------------------------------------
        if action_type in {
            "read_file",
            "write_file",
        }:
            path = action.get(
                "path"
            )

            if (
                not isinstance(path, str)
                or not path.strip()
            ):
                raise ValueError(
                    f"{action_type} requires a non-empty path."
                )

            normalized["path"] = path.strip()

        # ------------------------------------------------------------
        # write_file
        # ------------------------------------------------------------
        if action_type == "write_file":
            content = action.get(
                "content"
            )

            if not isinstance(
                content,
                str,
            ):
                raise ValueError(
                    "write_file requires string content."
                )

            normalized["content"] = content

        # ------------------------------------------------------------
        # run_command
        # ------------------------------------------------------------
        if action_type == "run_command":
            command = action.get(
                "command"
            )

            if (
                not isinstance(
                    command,
                    str,
                )
                or not command.strip()
            ):
                raise ValueError(
                    "run_command requires a non-empty command."
                )

            normalized["command"] = command.strip()

        # ------------------------------------------------------------
        # finish
        # ------------------------------------------------------------
        if action_type == "finish":
            summary = action.get(
                "summary"
            )

            if (
                not isinstance(
                    summary,
                    str,
                )
                or not summary.strip()
            ):
                raise ValueError(
                    "finish requires a non-empty summary."
                )

            normalized["summary"] = cls._tail(
                summary.strip(),
                4000,
            )

        return normalized
