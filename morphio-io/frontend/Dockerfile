# syntax=docker/dockerfile:1.7
# Purpose: Build the production Next.js frontend image.
# Responsibilities: Install pnpm dependencies, compile the Next.js app, and package the runtime server as a non-root user.
# Scope: Frontend production image only; development compose uses frontend/Dockerfile.dev.
# Usage: docker buildx build --load -f morphio-io/frontend/Dockerfile -t morphio-io-frontend:local morphio-io
# Invariants/Assumptions: pnpm-lock.yaml and packageManager are dependency sources of truth; Docker/BuildKit caches may be reused because lockfiles and copied source layers invalidate stale inputs.
# Stage 1: Build the Next.js application
FROM node:25-alpine AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN npm install -g corepack --force \
 && corepack enable \
 && corepack prepare "$(node -p "require('./package.json').packageManager")" --activate
RUN apk add --no-cache python3 make g++
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Set build env vars
ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Copy the rest of the frontend code and build
COPY frontend .
RUN pnpm build

# Stage 2: Serve the Next.js application
FROM node:25-alpine

WORKDIR /app

# Set runtime env vars
ENV NODE_ENV=production

# Create non-root user first
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs \
 && mkdir -p /app/.next/cache \
 && chown -R nextjs:nodejs /app

# Copy only necessary files
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./
COPY --from=builder --chown=nextjs:nodejs /app/pnpm-lock.yaml ./
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/next.config.ts ./
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/src ./src
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules

# Keep pnpm bootstrap aligned with the integrity-pinned packageManager from package.json
RUN npm install -g corepack --force \
 && corepack enable \
 && corepack prepare "$(node -p "require('./package.json').packageManager")" --activate

USER nextjs

ENV PORT=3005
EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:3005 || exit 1

CMD ["pnpm", "start"]
