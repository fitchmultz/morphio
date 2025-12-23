# Models Documentation

## Overview

SQLAlchemy async models in `app/models/`. Uses PostgreSQL in production, SQLite for development.

## Core Models

### User (`user.py`)

```python
class User(Base):
    id: int
    email: str (unique)
    display_name: str
    hashed_password: str
    is_admin: bool
    is_active: bool
    subscription_id: int (FK)
    created_at, updated_at, deleted_at
```

### Content (`content.py`)

```python
class Content(Base):
    id: int
    user_id: int (FK)
    template_id: int (FK, optional)
    title: str
    transcript: str
    generated_content: str
    source_type: str (video, audio, web, log)
    source_url: str (optional)
    created_at, updated_at, deleted_at
```

### Template (`template.py`)

```python
class Template(Base):
    id: int
    user_id: int (FK, nullable for system templates)
    name: str
    description: str
    content_template: str
    is_system: bool
```

## Usage & Billing Models

### Usage (`usage.py`)

```python
class Usage(Base):
    id: int
    user_id: int (FK)
    usage_type: str (VIDEO_PROCESSING, AUDIO_PROCESSING, etc.)
    usage_count: int
    usage_credits: int
    updated_at: datetime
```

### LLMUsageRecord (`llm_usage.py`)

```python
class LLMUsageRecord(Base):
    id: int
    user_id: int (FK)
    content_id: int (FK, optional)
    model: str
    input_tokens: int
    output_tokens: int
    cost: float (optional)
    created_at: datetime
```

### Subscription (`subscription.py`)

```python
class Subscription(Base):
    id: int
    plan: str (free, pro, enterprise)
    credits_limit: int
```

## Relationships

- User → many Content, Usage, LLMUsageRecord
- User → one Subscription
- Content → many Comment, Conversation
- Content → one Template (optional)

## Soft Deletion

Most models support soft deletion via `deleted_at` timestamp. Use `is_deleted` property to check.

## Related Files

- `app/models/` - Model definitions
- `db/versions/` - Alembic migrations
- `alembic.ini` - Migration config