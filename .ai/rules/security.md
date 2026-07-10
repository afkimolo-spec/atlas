# Atlas Security Rules

## Security Principles

- Security is considered during design.
- Never expose secrets.
- Avoid insecure defaults.
- Validate external inputs.

## Privilege Model

Atlas operates as an unprivileged user by default.

Normal engineering activities—including source code changes, documentation, testing, Git operations, local tooling, containers running in user space, and AI workflows—must not require elevated privileges.

Administrative operations affecting the host operating system (such as package installation, system services, firewall configuration, or changes under /etc, /usr, or /opt) require explicit elevation and should be performed deliberately.

## Infrastructure

- Monitor services.
- Keep systems patched.
- Restrict unnecessary access.
- Maintain audit trails.

## Credentials

Never store:

- Passwords
- API keys
- Tokens
- Private certificates

inside the workspace.
