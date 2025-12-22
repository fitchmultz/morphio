# Admin User Setup

This directory contains utility scripts for administration tasks.

## Creating an Admin User

There are three ways to create an admin user in the system:

### 1. Automatic Creation on Startup

The system will automatically create an admin user on startup if:

- No admin user already exists
- The `ADMIN_PASSWORD` environment variable is set

To use this method, set these environment variables when deploying:

```bash
ADMIN_EMAIL="admin@morphio.io"  # Optional, default: admin@morphio.io
ADMIN_PASSWORD="YourStrongPassword"  # Required for admin creation
ADMIN_NAME="Administrator"  # Optional, default: Administrator
```

You can set these in your deployment environment, docker-compose file, or pass them directly when running the Docker container:

```bash
docker run -e ADMIN_PASSWORD="YourStrongPassword" -e ADMIN_EMAIL="admin@yourdomain.com" your-image-name
```

### 2. Using the Command-Line Script

You can manually create an admin user by running the included script:

```bash
cd backend
python -m scripts.create_admin --password="YourStrongPassword" --email="admin@yourdomain.com" --name="Admin User"
```

The `--password` argument is required, while `--email` and `--name` are optional with defaults.

### 3. Using Docker Exec

If your application is already running in a Docker container, you can execute the script inside the container:

```bash
docker exec -it your-container-name python -m scripts.create_admin --password="YourStrongPassword"
```

## Important Notes

- If an admin user already exists with any email, no new admin will be created automatically
- If a user exists with the specified admin email but is not an admin, they will be upgraded to admin role
- Passwords should be strong and secure
- In production, use environment variables or secrets management for sensitive data

## Database Backup & Restore (PostgreSQL)

These scripts rely on `DATABASE_URL` being set (e.g., `postgresql://user:pass@host:5432/db`).

### Backup

```bash
export DATABASE_URL=postgresql://user:pass@postgres:5432/morphio
./scripts/db_backup.sh backups/morphio_$(date +%F).dump
```

### Restore

```bash
export DATABASE_URL=postgresql://user:pass@postgres:5432/morphio
./scripts/db_restore.sh backups/morphio_2025-09-01.dump
```

Notes:
- Backups use `pg_dump -Fc` (custom format) for fast, consistent dumps.
- Restores use `pg_restore --clean --if-exists` to drop/replace objects.
- Keep backups off the app host and rotate on a schedule.
