# Goals Graph Architecture

## Overview

The Aimi backend uses a unified goals graph architecture where all objectives are represented as nodes in a directed acyclic graph (DAG). This replaces the previous goals/tasks separation with a single, flexible goal hierarchy.

## Core Concept

**Everything is a goal.** Whether it's a high-level objective like "Become a Backend Developer" or a specific action like "Install Python", all nodes in the system are goals that can be:
- Completed independently
- Broken down into sub-goals
- Connected through dependencies
- Tracked with deadlines and priorities

## Goal Statuses

Goals have four possible statuses:

- `todo` - Ready for work (all dependencies completed)
- `blocked` - Cannot start (waiting for dependencies)
- `done` - Successfully completed
- `canceled` - Abandoned or no longer relevant

Status transitions are automatic based on dependency completion and user actions.

## Graph Rules and Validation

### 1. Acyclic Constraint
The graph must remain a DAG - no cycles are allowed. If adding a dependency would create a cycle, the operation is rejected.

### 2. Transitive Reduction
Direct dependencies are forbidden if an indirect path exists:
- ❌ Invalid: `A → C` when `A → B → C` exists
- ✅ Valid: `A → B → C` (single path)
- ✅ Valid: `A → B → C` and `A → D → C` (multiple paths with different intermediates)

### 3. AND Logic for Dependencies
A goal becomes `todo` only when ALL incoming dependencies are `done`. This ensures proper sequencing and prevents premature starts.

## LLM Integration

The LLM system provides several automated functions:

### Goal Discovery
- Analyzes chat messages to identify potential goals
- Suggests goal creation with appropriate context
- Maintains conversation flow while capturing objectives

### Duplicate Detection
- Uses embeddings to find semantically similar goals
- Proposes goal merging with dependency consolidation
- Rebuilds graph structure after merges

### Proactive Decomposition
- Monitors goal progress and deadlines
- Suggests breaking complex goals into sub-goals
- Triggered by missed deadlines or user requests
- Analyzes goal complexity and provides breakdown frameworks

### Graph Maintenance
- Validates new dependencies before creation
- Automatically updates goal statuses when dependencies complete
- Prevents invalid graph states through real-time validation

## Embeddings and Similarity

Goals maintain vector embeddings for semantic analysis:

- **Context Vectors**: Generated from goal title, description, and chat context (last 50 messages)
- **Summary Text**: Human-readable summary stored alongside vector for debugging and incremental updates
- **Similarity Search**: Find related goals for merging or reference using cosine similarity
- **Clustering**: Group related goals for visualization and organization
- **Evolution Tracking**: Update embeddings as goals develop through conversation

### Embedding Update Triggers
- Goal title or description changes
- Significant new chat context (every ~20 messages)
- Manual goal merge operations
- Periodic background refresh (weekly)

### Goal Merging Process
When combining similar goals:
1. LLM creates unified summary from both goals' summary_text
2. Generate new embedding from merged summary
3. Consolidate all dependencies and relationships
4. Archive duplicate goal while preserving history

## Data Structure

### Goals Table
```sql
- id: UUID (primary key)
- user_id: UUID (foreign key)
- chat_id: UUID (foreign key)
- title: TEXT (required)
- description: TEXT (optional)
- status: ENUM (todo/blocked/done/canceled)
- priority: INTEGER (1-5 scale)
- category: ENUM (career/health/learning/etc.)
- deadline: DATE (optional)
- estimated_duration_days: INTEGER (optional)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Goal Dependencies
```sql
- id: UUID (primary key)
- parent_goal_id: UUID (required before dependent)
- dependent_goal_id: UUID (requires parent first)
- dependency_type: ENUM (requires/enables/blocks/related/parallel)
- strength: INTEGER (1-5, importance of dependency)
- notes: TEXT (optional explanation)
- created_at: TIMESTAMP
```

### Goal Embeddings
```sql
- id: UUID (primary key)
- goal_id: UUID (foreign key)
- summary_text: TEXT (human-readable context summary)
- embedding: VECTOR(1536) (OpenAI embedding of summary_text)
- content_hash: TEXT (for change detection)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

## User Experience Flow

1. **Goal Creation**: LLM identifies objectives in conversation and creates goals
2. **Dependency Mapping**: System suggests logical prerequisites and sequences
3. **Status Tracking**: Users see available (`todo`) goals and blocked dependencies
4. **Progress Updates**: Completing goals automatically unlocks dependents
5. **Graph Evolution**: Goals can be split, merged, or restructured as understanding develops

## Visualization Concepts

Goals can be presented as:

- **Dependency Graph**: Traditional node-edge visualization showing relationships
- **Goal Cloud**: Clustered view with size indicating priority/complexity
- **Timeline View**: Deadline-based linear presentation
- **Category Matrix**: Goals organized by type and status
- **Progress Tree**: Hierarchical view showing completion status

The graph structure supports all these presentation modes while maintaining data integrity and relationship clarity.