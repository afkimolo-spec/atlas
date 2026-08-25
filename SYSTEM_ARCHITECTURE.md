# Atlas System Architecture

## Overview

Atlas is a local autonomous engineering system designed to coordinate
specialized AI agents, persistent engineering memory, planning, execution,
recovery, review, and operational workflows.

The system is designed around locally hosted LLM inference rather than
external model APIs.

## Core Architecture

The major layers are:

    API
      |
      v
    Workflow Orchestration
      |
      +-------------------------------+
      |                               |
      v                               v
    Task Planning                Execution State
      |                               |
      v                               v
    Specialized Agents          Recovery / Persistence
      |
      v
    Context Manager
      |
      +--------------------+
      |                    |
      v                    v
    History Store       Knowledge Index
      |                    |
      +---------+----------+
                |
                v
          Local SQLite Memory
                |
                v
          Local LLM Services

## Agent Layer

Atlas contains specialized agents for:

- Architecture
- Development
- Research
- Review
- Operations

The workflow layer routes each execution stage to the appropriate agent.

## Model Routing

### Agent Model

Model:

Qwen3-Coder-30B-A3B-Instruct

Endpoint:

    http://localhost:8002/v1

Used for:

- Architecture
- Development
- Agent workflows

### Research Model

Model:

Qwen2.5-Coder-32B-Instruct

Endpoint:

    http://localhost:8003/v1

Used for:

- Research
- Reviews
- Complex analysis

### Fast Model

Model:

Qwen2.5-Coder-7B-Instruct

Endpoint:

    http://localhost:8001/v1

Used for:

- Lightweight assistance
- Fast completion

### Embedding Model

Model:

nomic-embed-text

Endpoint:

    http://localhost:8000

Used by the knowledge indexing subsystem.

## Memory Architecture

Atlas maintains two primary persistent memory mechanisms.

### Session History

Stores conversational and execution history.

### Knowledge Index

Stores semantic engineering knowledge and retrieves relevant documents
using embeddings.

The primary persistent database is:

    .ai/memory/db/atlas.db

## Execution Architecture

Execution is represented by an explicit state machine.

Execution supports:

- Created
- Running
- Paused
- Retry
- Failed
- Completed
- Terminal state detection
- Stage-level state
- Execution history
- Persistent snapshots
- Restoration after process termination

## Recovery

The recovery subsystem evaluates failed stages using a deterministic
retry policy.

Recovery decisions include:

- Retry
- Fail
- Cancel

Execution state and recovery state are persisted so recovery can continue
after process termination.

## Workflow Architecture

A task is converted into a TaskPlan.

The workflow executor:

1. Creates a session.
2. Creates or receives a task plan.
3. Determines dependency-ready stages.
4. Routes each stage to its agent.
5. Executes the stage.
6. Persists execution state.
7. Records output.
8. Recovers failed stages where permitted.
9. Continues until completion or terminal failure.

The plan, rather than a fixed hard-coded sequence, is the source of truth
for stage execution.

## Data Flow

The primary execution flow is:

    User Task
       |
       v
    Session
       |
       v
    Task Planner
       |
       v
    Task Plan
       |
       v
    Execution State Machine
       |
       v
    Agent
       |
       v
    Context Manager
       |
       +--------------------+
       |                    |
       v                    v
    Session History     Knowledge Index
       |                    |
       +---------+----------+
                 |
                 v
             LLM Client
                 |
                 v
          Local LLM Endpoint
                 |
                 v
             Agent Output
                 |
                 v
          Execution State
                 |
                 v
        Persistent Execution Store

## Network Requirements

Current local inference endpoints:

- TCP 8000
- TCP 8001
- TCP 8002
- TCP 8003

MySQL-related infrastructure may exist independently of Atlas and is not
assumed to be an Atlas runtime dependency unless explicitly configured.

## Storage Requirements

Atlas requires storage for:

- Source code
- .ai persistent state
- SQLite database
- llama.cpp
- Runtime scripts
- GGUF models
- Logs
- Temporary runtime data

GGUF files are intentionally maintained outside source control.

## Security Considerations

The operational installation may contain environment configuration,
credentials, tokens, and other machine-specific information.

The migration snapshot is intentionally designed to preserve the current
installation for private migration purposes.

Before making the repository public, perform a dedicated secret and
credential review.

## External Runtime Components

The operational installation includes resources outside the repository:

    /opt/llama.cpp
    /opt/scripts
    /opt/models

The migration package captures the first two and records the third.

## Authoritative Migration Information

Operational reconstruction information is contained in:

- MIGRATION_GUIDE.md
- ENVIRONMENT_TEMPLATE.md
- DEPENDENCIES.md
- migration/MIGRATION_MANIFEST.txt
- migration/manifest/
- migration/system/
- migration/runtime/
