# Atlas Development History

## Purpose

This document preserves the major architectural and implementation
milestones of Atlas so development can continue without relying on
conversation history.

## Initial Architecture

Atlas was designed as a local autonomous engineering system using
specialized agents and locally hosted LLM inference.

The architecture deliberately avoided dependency on Ollama.

## Model Runtime Decision

### llama.cpp

Decision:

Use llama.cpp instead of Ollama.

Rationale:

- Lower runtime overhead
- Direct GGUF support
- Better control over local inference
- Greater control over model/server configuration

## Model Routing

Atlas established separate model roles.

### Qwen3 Coder

Primary engineering and agent model.

Endpoint:

    http://localhost:8002/v1

### Qwen2.5 Coder 32B

Research and complex-analysis model.

Endpoint:

    http://localhost:8003/v1

### Qwen2.5 Coder 7B

Fast model for low-latency assistance.

Endpoint:

    http://localhost:8001/v1

### nomic-embed-text

Embedding model.

Endpoint:

    http://localhost:8000

## Persistent Memory

Atlas introduced persistent memory consisting of:

- Session history
- Semantic knowledge
- SQLite persistence
- Vector/embedding support

The persistent database is:

    .ai/memory/db/atlas.db

## Context Management

The ContextManager was introduced to combine:

1. Relevant engineering knowledge
2. Persistent session history
3. Current task

This produces model-ready context for agents.

## Execution State Machine

Atlas evolved from direct agent execution into explicit execution-state
management.

The execution subsystem introduced:

- Execution states
- Stage states
- State transitions
- Transition validation
- Execution history
- Snapshots
- Terminal state detection

Invalid state transitions are explicitly rejected.

## Retry and Recovery

Stage retry behavior was introduced through:

- Retry attempt tracking
- RecoveryPolicy
- RecoveryDecision
- RecoveryManager

The system distinguishes retryable failures from terminal failures.

## Execution Persistence

Execution snapshots were persisted to SQLite.

The system can:

- Save execution state
- Load execution state
- Restore stage state
- Preserve execution history
- Continue an incomplete execution after process termination

## Session Persistence

Session persistence was added so session identity and state survive
beyond an individual process.

## Autonomous Plan Execution

The workflow system was expanded to execute TaskPlan objects autonomously.

The executor:

1. Finds dependency-ready stages.
2. Selects the correct agent.
3. Executes the stage.
4. Records output.
5. Advances the execution.
6. Handles failures.
7. Applies recovery.
8. Persists state.

This removed dependence on a manually hard-coded execution sequence.

## Autonomous Recovery

Recovery was integrated into autonomous execution.

A failed execution can be:

1. Detected.
2. Persisted.
3. Evaluated against retry policy.
4. Retried.
5. Restored after process interruption.
6. Completed if the retry succeeds.
7. Terminated after retry exhaustion.

## Verification Milestones

The following subsystems have been independently verified:

- Session state
- Persistent memory
- Execution state machine
- Execution retry
- Recovery manager
- Execution persistence
- Execution restoration
- Session persistence
- Autonomous execution
- Autonomous plan execution
- Autonomous recovery
- Recovery exhaustion
- Agent context
- Agent runtime
- Model routing
- Workflow execution
- Planner behavior
- Tool execution
- Workspace protection

## Current Architectural Position

Atlas has moved beyond an experimental single-agent architecture into
a persistent multi-agent execution framework with:

- Planning
- Specialized agents
- Context retrieval
- Persistent memory
- Execution state
- Stage dependencies
- Retry
- Recovery
- Snapshot persistence
- Restoration
- Autonomous workflows

## Current Operational Objective

The next development stages should focus on production hardening rather
than rebuilding the execution foundation.

Priority areas include:

- Authentication
- Docker deployment
- Logging improvements
- Operational observability
- Resource management
- Concurrency control
- Feedback mechanisms
- Production API hardening
- Deployment automation
- Comprehensive integration testing

## Lessons Learned

### Explicit state is preferable to implicit execution

Execution state must be represented directly and persisted.

### Recovery must be deterministic

Retry behavior should be governed by an explicit policy rather than
ad-hoc exception handling.

### Persistent state must survive process boundaries

Execution and session state cannot depend exclusively on in-memory objects.

### Plans should define execution dependencies

The workflow executor should consume the TaskPlan as its source of truth.

### Local model services should remain independently addressable

Separate endpoints allow different model sizes to be selected according
to task complexity and latency requirements.

## Current State

The operational state of the installation is preserved by the migration
package.

See:

- MIGRATION_GUIDE.md
- ENVIRONMENT_TEMPLATE.md
- DEPENDENCIES.md
- migration/MIGRATION_MANIFEST.txt
