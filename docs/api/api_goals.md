# Goals Endpoints

## List user goals
- **Method**: `GET`
- **Path**: `/v1/goals/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `status` (optional): Filter by goal status (`active`, `completed`, `paused`, `cancelled`)
- **Response** (`SuccessResponse[GoalListResponse]`):

```json
{
  "status": "success",
  "data": {
    "goals": [
      {
        "goal_id": "uuid",
        "title": "Learn Python",
        "description": "Complete Python course and build projects",
        "status": "active",
        "category": "learning",
        "priority": 4,
        "estimated_duration_days": 90,
        "difficulty_level": 6,
        "deadline": "2025-03-01",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-15T00:00:00+00:00",
        "tasks": [
          {
            "task_id": "uuid",
            "title": "Watch intro videos",
            "description": "Complete first 5 lessons",
            "status": "pending",
            "estimated_hours": 10,
            "due_date": "2025-01-20T00:00:00+00:00",
            "reminder_at": null,
            "created_at": "2025-01-01T00:00:00+00:00"
          }
        ]
      }
    ],
    "total": 1
  }
}
```

## Get specific goal
- **Method**: `GET`
- **Path**: `/v1/goals/{goal_id}`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response** (`SuccessResponse[GoalItem]`):

```json
{
  "status": "success",
  "data": {
    "goal_id": "uuid",
    "title": "Learn Python",
    "description": "Complete Python course and build projects",
    "status": "active",
    "category": "learning",
    "priority": 4,
    "estimated_duration_days": 90,
    "difficulty_level": 6,
    "deadline": "2025-03-01",
    "created_at": "2025-01-01T00:00:00+00:00",
    "updated_at": "2025-01-15T00:00:00+00:00",
    "tasks": [
      {
        "task_id": "uuid",
        "title": "Watch intro videos",
        "description": "Complete first 5 lessons",
        "status": "pending",
        "estimated_hours": 10,
        "due_date": "2025-01-20T00:00:00+00:00",
        "reminder_at": null,
        "created_at": "2025-01-01T00:00:00+00:00"
      },
      {
        "task_id": "uuid2",
        "title": "Build first project",
        "description": "Create a simple calculator",
        "status": "in_progress",
        "estimated_hours": 20,
        "due_date": "2025-02-01T00:00:00+00:00",
        "reminder_at": "2025-01-25T09:00:00+00:00",
        "created_at": "2025-01-10T00:00:00+00:00"
      }
    ]
  }
}
```

## Get mental state history
- **Method**: `GET`
- **Path**: `/v1/goals/mental-states/`
- **Headers**: `Authorization: Bearer <access_token>`
- **Query Parameters**:
  - `limit` (optional): Number of records to return (1-100, default: 50)
  - `offset` (optional): Number of records to skip (default: 0)
- **Response** (`SuccessResponse[MentalStateListResponse]`):

```json
{
  "status": "success",
  "data": {
    "mental_states": [
      {
        "mental_state_id": "uuid",
        "mood": "focused",
        "energy_level": 8,
        "confidence_level": 7,
        "detected_emotions": ["excitement", "determination"],
        "context": "Working on Python project, feeling motivated",
        "analysis_source": "summary",
        "created_at": "2025-01-15T14:30:00+00:00"
      }
    ],
    "total": 1
  }
}
```

## Task Ordering

Tasks within goals are automatically sorted by:
1. **Status priority**: `pending` → `in_progress` → `completed` → `cancelled`
2. **Due date**: Nearest due dates first (null dates last)
3. **Creation date**: Oldest tasks first

## Field Descriptions

### Goal Fields
- `status`: Goal status (`active`, `completed`, `paused`, `cancelled`)
- `category`: Goal category (`career`, `health`, `learning`, `finance`, `personal`, `social`, `creative`)
- `priority`: Importance level (1-5, higher is more important)
- `estimated_duration_days`: Expected time to complete goal
- `difficulty_level`: Complexity rating (1-10)

### Task Fields
- `status`: Task status (`pending`, `in_progress`, `completed`, `cancelled`)
- `estimated_hours`: Expected time to complete task

### Mental State Fields
- `energy_level`: Energy rating (1-10)
- `confidence_level`: Confidence rating (1-10)
- `detected_emotions`: Array of emotion keywords
- `analysis_source`: How state was determined (`summary`, `direct`, etc.)

> **Note**: Goals and tasks are read-only through this API. Creation and modification are handled by the LLM using specialized tools during chat conversations.