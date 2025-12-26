# Morphio Roadmap

> **Last Updated:** 2025-12-25

This document tracks future work items and enhancement ideas for the Morphio project.

## Recently Completed

These items were completed in the documentation normalization work:

- [x] Align ports, versions, and env examples with backend config
- [x] Add admin export bearer auth + unified API base URL
- [x] Add API key management UI (create/revoke/list)
- [x] Align log upload limits with backend config + config endpoint
- [x] Add Prometheus request metrics middleware
- [x] Add backend tests for log config + upload size enforcement
- [x] Add frontend tests for API key flows
- [x] Create canonical status page (`docs/status.md`)
- [x] Create configuration guide (`docs/configuration.md`)
- [x] Align env examples across stack/backend/frontend
- [x] Standardize Redis connection behavior (URL with `/0`)
- [x] Enforce provider SDK boundary with audit script
- [x] Fill empty backend docs with real content
- [x] Surface job stage progress in frontend UI
- [x] Add `/user/credits` endpoint
- [x] Add usage/credits panel to Profile page

## Short-Term (Next Sprint)

### Developer Experience
- [ ] Add pre-commit hooks for SDK boundary enforcement
- [ ] Create contributor onboarding guide
- [ ] Add development troubleshooting FAQ

### Testing
- [ ] Add E2E tests for credits display flow
- [ ] Add integration tests for stage progress updates
- [ ] Improve test coverage for usage tracking

### Documentation
- [ ] Add API examples to OpenAPI docs
- [ ] Create architecture decision records (ADRs)
- [ ] Document upgrade procedures

## Medium-Term (This Quarter)

### Features
- [x] Export LLM usage reports (CSV) - Admin can export usage data with date filters
- [x] Add usage alerts when approaching limit - Warning/critical banners in Profile
- [x] Implement plan upgrade flow in UI - Stripe checkout integration
- [x] Add API key authentication for programmatic access - Bearer token auth with scopes

### Performance
- [ ] Profile and optimize transcript generation
- [ ] Add caching layer for frequently accessed content
- [ ] Optimize database queries in usage tracking

### Infrastructure
- [ ] Set up staging environment
- [x] Add Prometheus metrics endpoint
- [ ] Configure log aggregation
- [ ] Add health check dashboard

## Long-Term (This Year)

### Platform
- [ ] Multi-tenant workspace support
- [ ] Batch processing API
- [ ] WebSocket-based real-time updates

### Integrations
- [ ] Slack notifications
- [ ] Calendar integration for scheduled processing

### Scalability
- [ ] Kubernetes deployment manifests
- [ ] Horizontal scaling for workers
- [ ] CDN integration for media delivery

## Ideas Backlog

These are ideas that need further discussion and prioritization:

- Voice cloning integration
- Multi-language transcript support
- Collaborative editing of generated content
- Template marketplace
- Mobile app (React Native)
- Browser extension for quick captures

## How to Contribute

1. Pick an item from **Short-Term** or **Medium-Term**
2. Create an issue to discuss the approach
3. Reference this roadmap in your PR

## Related Docs

- [Status](./status.md) - Current project state
- [Configuration](./configuration.md) - Environment setup
- [Architecture](./architecture.md) - System design
