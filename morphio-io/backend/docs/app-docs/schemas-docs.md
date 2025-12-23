# Schemas Documentation

## Overview

Pydantic schemas in `app/schemas/` define request/response contracts. Generated OpenAPI types are used by the frontend.

## Key Schemas

### Job Status (`job_schema.py`)

```python
class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    stage: Optional[ProcessingStage]  # QUEUED, DOWNLOADING, etc.
    message: Optional[str]
    result: Optional[Any]
    error: Optional[str]
```

`ProcessingStage` enum (from `app/utils/enums.py`):
- QUEUED, DOWNLOADING, CHUNKING, TRANSCRIBING
- DIARIZING, GENERATING, SAVING, COMPLETED, FAILED

### Media Status (`media_schema.py`)

```python
class MediaProcessingStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    stage: Optional[ProcessingStage]
    message: Optional[str]
    result: Optional[MediaResult]
    error: Optional[str]
```

### Content (`content_schema.py`)

```python
class ContentOut(BaseModel):
    id: int
    title: str
    transcript: str
    generated_content: str
    source_type: str
    source_url: Optional[str]
    template: Optional[TemplateOut]
    created_at: datetime
```

### User (`user_schema.py`)

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    is_admin: bool
```

### Auth (`auth_schema.py`)

```python
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

## Response Wrappers

Standard response format via `app/utils/response_utils.py`:

```python
{
    "status": "success" | "error",
    "message": "Human-readable message",
    "data": { ... }  # Actual payload
}
```

## Frontend Type Generation

Types are generated from OpenAPI spec:
```bash
cd morphio-io/frontend
pnpm openapi:refresh  # Backend must be running on port 8000
```

Generated files in `frontend/src/client/` - **do not edit manually**.

## Related Files

- `app/schemas/` - Schema definitions
- `app/utils/response_utils.py` - Response helpers
- `frontend/src/client/types.gen.ts` - Generated frontend types