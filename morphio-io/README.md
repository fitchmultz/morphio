# Morphio - AI-Powered Content Generation Platform

Morphio is a modern, full-stack web application designed for creating, managing, and processing content with the aid of artificial intelligence. Built with a NextJS frontend and a FastAPI backend, Morphio leverages cutting-edge technologies to provide users with a seamless experience for generating content from various media sources and web inputs.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [AI and Machine Learning Integration](#ai-and-machine-learning-integration)
- [Current Functionality](#current-functionality)
- [Setup and Installation](#setup-and-installation)
- [Secrets & Production](#secrets--production)
 - [Releases](#releases)
 - [Database](#database)
- [Potential Use Cases](#potential-use-cases)
- [Contributing](#contributing)

## Tech Stack

### Frontend

- **Next.js 16.1.1**: React framework for server-side rendering and static site generation
- **React 19.0.0**: Component-based UI library
- **TailwindCSS 4+**: Utility-first CSS framework for rapid styling
- **TypeScript**: Static typing for enhanced code quality
- **Zustand**: State management
- **React Query**: Data fetching and caching

### Backend

- **Python 3.13**: Core programming language
- **FastAPI**: High-performance web framework for building APIs
- **SQLAlchemy**: ORM for database interactions
- **Alembic**: Database migration tool
- **PostgreSQL**: Primary database (assumed based on SQLAlchemy usage)
- **Redis**: Caching and job queuing

### DevOps

- **Docker**: Containerization for consistent deployment
- **NGINX**: Reverse proxy for routing frontend/backend traffic
- **GitHub Actions**: CI/CD workflows for automated building and deployment

## Architecture

Morphio follows a client-server architecture with a clear separation of concerns:

- **Frontend (NextJS)**:

  - Located in `frontend/`
  - Handles UI rendering, user interactions, and API calls
  - Uses components (`src/components/`), hooks (`src/hooks/`), and a Zustand store (`src/store/`) for state management
  - Implements authentication, content generation forms, and template management

- **Backend (FastAPI)**:

  - Located in `backend/`
  - Organized into models (`app/models/`), routes (`app/routes/`), services (`app/services/`), and utilities (`app/utils/`)
  - Manages database operations, authentication, content processing, and admin functionalities
  - Uses asynchronous programming with SQLAlchemy for efficient database access

- **Database**:

  - Relational structure with tables for users, content, comments, templates, subscriptions, and usage tracking
  - Supports soft deletion for data recovery

- **Infrastructure**:
  - Dockerized services (`docker-compose.yml`, `Dockerfile`s) for backend and frontend
  - NGINX configurations for routing (`nginx-backend.conf`, `nginx-frontend.conf`)

## Key Features

- **User Authentication**: Secure registration, login, and token refresh using JWT (JSON Web Tokens)
- **Content Management**: Create, read, update, and delete (CRUD) operations for user-generated content
- **Template System**: Predefined and user-created templates for content generation (e.g., blog posts, social media posts)
- **Media Processing**: Asynchronous processing of uploaded files or URLs (YouTube, web content)
- **Comment System**: Hierarchical comments on content with soft deletion
- **Admin Panel**: Usage stats and subscription management for administrators
- **Rate Limiting & Caching**: Performance optimization and abuse prevention
- **Log Analysis**: Advanced log processing capabilities with intelligent pattern recognition
- **Data Anonymization**: Robust anonymization features for sensitive data in logs and content

## AI and Machine Learning Integration

Morphio integrates AI/ML capabilities primarily through its content generation services:

- **Content Generation Service (`generation_service.py`)**:

  - Processes media inputs (audio, video, web) to generate structured content
  - Likely interfaces with external AI models (e.g., LLMs like GPT or custom models) for text generation
  - Uses templates to format output (e.g., `blog-post.json`, `linkedin-post.json`)

- **Implementation Details**:

  - Asynchronous job processing for scalability
  - Supports multiple input sources (YouTube, file uploads, web scraping)
  - Configurable via templates stored in `backend/templates/`

- **Potential AI/ML Components**:
  - Natural Language Processing (NLP) for summarizing or rewriting content
  - Speech-to-text for audio/video transcription (`transcription_utils.py`)
  - Text generation for creating titles or full articles

While the exact AI models aren't specified in the codebase, the structure suggests integration with third-party APIs or local ML models, managed through the `generation_service.py` and related utilities.

## Current Functionality

- **Users**: Register, log in, manage profiles, and change passwords
- **Content**: Save, retrieve, update, and delete content with tags and comments
- **Templates**: Create and manage reusable content templates
- **Media Processing**: Upload files or provide URLs for AI-driven content generation
- **Admin**: Monitor usage and subscriptions (admin-only routes)
- **Log Analysis**: Process and analyze log files with AI-powered pattern detection
- **Anonymization**: Automatically detect and anonymize sensitive information in logs and content

## Setup and Installation

1. **Prerequisites**:

   - Node.js >= 24.0.0
   - Python 3.13
   - Docker and Docker Compose
   - PostgreSQL and Redis instances (or use Docker; Redis port 6384)

2. **Clone the Repository**:

   ```bash
   git clone <repository-url>
   cd morphio-io
   ```

3. **Backend Setup**:

  ```bash
  cp .env.example .env  # Edit with your credentials (optional overrides in .env.local)
  cd backend
  uv sync --dev         # Install project deps + dev tools (ruff, pytest, etc.)
  alembic upgrade head  # Run database migrations
  ```

4. **Frontend Setup**:

   ```bash
   cd frontend
   pnpm install
   pnpm dev  # Start development server
   ```

5. **Docker Setup**:

   ```bash
   cp .env.example .env  # Configure environment variables
   make dev-docker
   ```

   **Platform Note**: The `worker-ml` service is amd64-only due to `torchcodec` (a `pyannote-audio` dependency) lacking Linux ARM64 wheels. Docker Compose files include `platform: linux/amd64` for this service. For manual builds on ARM64:

   ```bash
   DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -f backend/Dockerfile.worker-ml ..
   ```

6. **Access**:
   - Frontend: `http://localhost:3005`
   - Backend API: `http://localhost:8005`

## Secrets & Production

- Required in production (`APP_ENV=production`):
  - `SECRET_KEY` and `JWT_SECRET_KEY` must be strong, non-default values. The API refuses to start if either is empty or still set to dev defaults.
  - Other sensitive vars should be set via env or Docker secrets (e.g., `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`).

- Docker secrets support:
  - Provide file-based secrets using `*_FILE` env vars or by mounting `/run/secrets/<NAME>`.
  - Supported names: `SECRET_KEY`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `DB_PASSWORD`, `REDIS_PASSWORD`.

- Example (Compose):

  ```yaml
  services:
    backend:
      environment:
        - APP_ENV=production
        - SECRET_KEY_FILE=/run/secrets/SECRET_KEY
        - JWT_SECRET_KEY_FILE=/run/secrets/JWT_SECRET_KEY
        - OPENAI_API_KEY_FILE=/run/secrets/OPENAI_API_KEY
      secrets:
        - SECRET_KEY
        - JWT_SECRET_KEY
        - OPENAI_API_KEY

  secrets:
    SECRET_KEY:
      file: ./secrets/SECRET_KEY
    JWT_SECRET_KEY:
      file: ./secrets/JWT_SECRET_KEY
    OPENAI_API_KEY:
      file: ./secrets/OPENAI_API_KEY
  ```

### Production Compose

- Use `docker-compose.prod.yml` to run split services with secrets:

  ```bash
  # Prepare secrets (example)
  mkdir -p secrets
  printf '%s' 'postgresql+asyncpg://user:pass@postgres:5432/morphio' > secrets/DATABASE_URL
  openssl rand -base64 48 > secrets/SECRET_KEY
  openssl rand -base64 48 > secrets/JWT_SECRET_KEY
  printf '%s' 'redis://:$(cat secrets/REDIS_PASSWORD)@redis:6384/0' > secrets/REDIS_URL
  openssl rand -hex 24 > secrets/REDIS_PASSWORD

  # Bring up stack (API will refuse to start if required secrets are missing or invalid)
  docker compose -f docker-compose.prod.yml up -d --build
  ```

  - Backend refuses to start if:
    - `APP_ENV=production` and `SECRET_KEY`/`JWT_SECRET_KEY` are missing or still dev defaults
    - `DATABASE_URL` is missing or points to SQLite

See `.env.example` for more details.

## Releases

### What gets produced

- Three images in GHCR, tagged with your semver tag (e.g., v1.2.3):
  - `ghcr.io/<owner>/morphio-io-backend-api`
  - `ghcr.io/<owner>/morphio-io-worker-ml`
  - `ghcr.io/<owner>/morphio-io-crawler`
- A generated `docker-compose.release.yml` that pins digests (`image@sha256:...`).
- SBOMs (SPDX JSON) for each image.

### How to cut a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions builds images, pushes to GHCR, generates the pinned compose + SBOMs, and attaches them to the GitHub Release.

### Deploy (pinned)

```bash
curl -fsSLO https://github.com/<org>/<repo>/releases/download/v1.0.0/docker-compose.release.yml
docker compose -f docker-compose.release.yml up -d
```

### Blue/Green quick steps

- Run the new stack as a separate project (green):

```bash
docker compose -p morphio-green -f docker-compose.release.yml up -d
```

- Point NGINX upstream to the green backend (or flip traffic at your ingress).
- After validation, stop the old stack:

```bash
docker compose -p morphio-blue down
```

### Canary

- Run both blue and green, split traffic at your reverse proxy (e.g., 10% to green via NGINX upstream weights).
- Increase weight as metrics and error budgets allow; roll back by restoring weight.

## Database

- Dev: Uses SQLite by default for simplicity.
- Prod: PostgreSQL required. Set `DATABASE_URL` (e.g., `postgresql+asyncpg://user:pass@host:5432/db`).
  The backend refuses to start with SQLite when `APP_ENV=production`.

## Potential Use Cases

Beyond its current role as a content generation tool, Morphio's architecture and AI integration open up several possibilities:

1. **Educational Platform**:

   - Convert lectures or webinars into study notes or summaries
   - Generate quizzes or flashcards from video/audio content

2. **Marketing Automation**:

   - Create bulk social media campaigns from a single source
   - Analyze competitor content and generate optimized responses

3. **Journalism Aid**:

   - Transcribe interviews and generate draft articles
   - Summarize press conferences into concise reports

4. **E-commerce Enhancement**:

   - Generate product descriptions from supplier videos or specs
   - Create SEO-optimized content for product pages

5. **Personal Knowledge Management**:

   - Process personal media (podcasts, videos) into organized notes
   - Build a searchable knowledge base with AI-tagged content

6. **Corporate Training**:
   - Transform training videos into written guides or manuals
   - Generate compliance documentation from regulatory updates

The modular design, with its template system and extensible backend services, makes Morphio adaptable to various domains requiring automated content processing.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add YourFeature"`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

For bugs or feature requests, open an issue with detailed information.

## Developer Tooling

- Python linting uses `ruff`; type checking uses `basedpyright` (basic mode). Settings live in `backend/pyproject.toml` (line length 100, Python 3.13).

  ```bash
  # From backend/
  uv run ruff check .
  uv run basedpyright
  ```
  
- Project dependencies are declared in `backend/pyproject.toml`.
