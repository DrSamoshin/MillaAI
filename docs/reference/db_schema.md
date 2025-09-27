# Database Schema - Aimi Backend

## Overview

The Aimi backend uses PostgreSQL with a unified goals graph architecture. The schema includes support for users, chats, messages, goals with dependencies, events, notifications, and mental state tracking. All objectives are represented as goals in a directed acyclic graph.

## Core Tables

### users
User accounts and authentication.

```sql
users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) UNIQUE,
    apple_id VARCHAR(255) UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Enums:**
- `user_role`: `user`, `admin`

**Indexes:**
- `ix_users_created_at` on `created_at`

### chats
Chat conversations between users and assistant.

```sql
chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT,
    model VARCHAR(100) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}',
    last_seq INTEGER NOT NULL DEFAULT 0,
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    archived BOOLEAN NOT NULL DEFAULT false
)
```

**Indexes:**
- `ix_chats_user_id` on `user_id`
- `ix_chats_last_active_at` on `last_active_at`
- `ix_chats_created_at` on `created_at`

### messages
Individual messages within chat conversations.

```sql
messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES chats(id),
    seq INTEGER NOT NULL,
    role messagerole NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    truncated BOOLEAN NOT NULL DEFAULT false,
    from_summary BOOLEAN NOT NULL DEFAULT false,
    request_id UUID
)
```

**Enums:**
- `messagerole`: `user`, `assistant`, `system`

**Indexes:**
- `ix_messages_chat_id_seq` on `(chat_id, seq)`
- `ix_messages_chat_id_created_at` on `(chat_id, created_at)`
- `ix_messages_request_id` on `request_id`
- `ix_messages_created_at` on `created_at`

### goal_embeddings
Vector embeddings of goals for semantic similarity search and duplicate detection.

```sql
goal_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    embedding VECTOR(1536) NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Indexes:**
- `ix_goal_embeddings_goal_id` on `goal_id`
- `ix_goal_embeddings_created_at` on `created_at`
- `ix_goal_embeddings_content_hash` on `content_hash`

### devices
User devices for push notifications.

```sql
devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    device_token VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    locale VARCHAR(10),
    timezone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Indexes:**
- `ix_devices_user_id` on `user_id`
- `ix_devices_device_token` on `device_token`
- `ix_devices_last_seen` on `last_seen`

## Goal Management System

### goals
User objectives in a unified goal graph. All objectives are goals regardless of complexity.

```sql
goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    category goalcategory,
    status goalstatus NOT NULL DEFAULT 'todo',
    priority INTEGER NOT NULL DEFAULT 3,
    estimated_duration_days INTEGER,
    deadline DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Enums:**
- `goalstatus`: `todo`, `blocked`, `done`, `canceled`
- `goalcategory`: `career`, `health`, `learning`, `finance`, `personal`, `social`, `creative`

**Constraints:**
- `valid_priority`: `priority BETWEEN 1 AND 5`

**Indexes:**
- `ix_goals_user_id` on `user_id`
- `ix_goals_chat_id` on `chat_id`
- `ix_goals_status` on `status`
- `ix_goals_deadline` on `deadline`


### goal_dependencies
Graph relationships between goals with validation for DAG structure.

```sql
goal_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    dependent_goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    dependency_type dependencytype NOT NULL DEFAULT 'requires',
    strength INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT no_self_dependency CHECK (parent_goal_id != dependent_goal_id),
    CONSTRAINT valid_strength CHECK (strength BETWEEN 1 AND 5),
    CONSTRAINT unique_dependency UNIQUE (parent_goal_id, dependent_goal_id)
)
```

**Enums:**
- `dependencytype`: `requires`, `enables`, `blocks`, `related`, `parallel`

**Indexes:**
- `ix_goal_dependencies_parent_goal_id` on `parent_goal_id`
- `ix_goal_dependencies_dependent_goal_id` on `dependent_goal_id`

**Graph Rules:**
- No cycles allowed (DAG constraint)
- No transitive dependencies (A→C forbidden if A→B→C exists)
- AND logic: goals become `todo` only when ALL dependencies are `done`


## Events and Notifications

### events
Calendar events and scheduled activities.

```sql
events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    event_type eventtype NOT NULL DEFAULT 'personal',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status eventstatus NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Enums:**
- `eventtype`: `work`, `meeting`, `break`, `focus_time`, `deadline`, `personal`
- `eventstatus`: `scheduled`, `completed`, `cancelled`, `in_progress`

**Indexes:**
- `ix_events_user_id` on `user_id`
- `ix_events_goal_id` on `goal_id`
- `ix_events_start_time` on `start_time`
- `ix_events_status` on `status`

### notifications
Smart notifications sent as assistant messages.

```sql
notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    notification_type notificationtype NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    status notificationstatus NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Enums:**
- `notificationtype`: `motivation`, `rest_suggestion`, `progress_check`, `goal_reminder`, `celebration`, `planning`
- `notificationstatus`: `pending`, `sent`, `dismissed`

**Indexes:**
- `ix_notifications_user_id` on `user_id`
- `ix_notifications_chat_id` on `chat_id`
- `ix_notifications_scheduled_for` on `scheduled_for`
- `ix_notifications_status` on `status`
- `ix_notifications_type` on `notification_type`

## Analytics

### mental_states
User mental state analysis from conversations.

```sql
mental_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    mood VARCHAR(50),
    energy_level INTEGER,
    confidence_level INTEGER,
    detected_emotions TEXT[],
    context TEXT,
    analysis_source VARCHAR(20) NOT NULL DEFAULT 'summary',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

## Relationships Overview

### User Domain
- `User` 1:N `Chat`
- `User` 1:N `Goal`
- `User` 1:N `Event`
- `User` 1:N `MentalState`
- `User` 1:N `Notification`

### Chat Domain
- `Chat` 1:N `Message`
- `Chat` 1:N `Goal`
- `Chat` 1:N `MentalState`
- `Chat` 1:N `Notification`

### Goal Domain
- `Goal` N:M `Goal` (via `goal_dependencies`)
- `Goal` 1:1 `GoalEmbedding`
- `Goal` 1:N `Event`
- `Goal` 1:N `Notification`

## Graph Operations

The unified goals graph supports operations for:

1. **Dependency Resolution**: Finding all prerequisites for any goal
2. **Impact Analysis**: Finding all goals that depend on a specific goal
3. **Status Propagation**: Automatically updating goal status based on dependencies
4. **Cycle Detection**: Preventing circular dependencies during creation
5. **Transitive Reduction**: Validating direct dependencies aren't redundant
6. **Similarity Search**: Finding duplicate or related goals using embeddings
7. **Critical Path**: Identifying bottlenecks in goal achievement chains

## Migration Notes

The schema uses PostgreSQL native enums for type safety and performance, with corresponding Python enums for application-level validation.

Vector embeddings use the `pgvector` extension for semantic similarity search and duplicate goal detection.

All timestamps are stored with timezone information (`TIMESTAMPTZ`).

The unified goals graph replaces the previous goals/tasks separation with a single flexible hierarchy.