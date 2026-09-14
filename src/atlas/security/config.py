from __future__ import annotations

from atlas.config.loader import load_security
from atlas.security.policy import SecurityPolicy


def load_security_policy() -> SecurityPolicy:
    config = load_security()

    return SecurityPolicy(
        allow_shell=config.allow_shell,
        allow_git=config.allow_git,
        allow_file_write=config.allow_file_write,
        allow_network=config.allow_network,
        require_review_before_commit=(
            config.require_review_before_commit
        ),
        block_system_paths=(
            list(config.block_system_paths)
        ),
    )
