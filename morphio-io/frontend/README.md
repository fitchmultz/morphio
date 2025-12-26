# Morphio Frontend

This is the frontend application for Morphio, a platform for generating content from YouTube videos or local video files.

## Getting Started

### Prerequisites

- Node.js v24 or higher (see `.nvmrc`)
- pnpm v10.17.0 (managed via `packageManager` field)

### Installation

1. Clone the repository
2. Navigate to the frontend directory
3. Use Node 24 (Corepack-enabled):

```bash
nvm use
corepack enable
# pnpm version is managed via package.json packageManager field
```

4. Install dependencies:

```bash
pnpm install
```

### Environment Variables

Copy the example environment file and modify as needed:

```bash
cp .env.example .env.local
```

Key environment variables:

- `NEXT_PUBLIC_API_BASE_URL`: URL for the backend API
- `NEXT_PUBLIC_ALLOWED_AUDIO_EXTENSIONS`: Array of allowed audio file extensions

## Development

Start the development server:

```bash
pnpm dev
```

The application will be available at [http://localhost:3005](http://localhost:3005).

### Tailwind CSS v4

- This project uses Tailwind CSS v4 with the new PostCSS plugin flow.
- PostCSS config uses `@tailwindcss/postcss` (see `postcss.config.mjs`).
- Plugins (typography, forms) are registered in CSS via `@plugin` directives in `src/app/globals.css`.
- A separate `tailwind.config.js` is not required and has been removed.

## Testing

The project uses Jest with React Testing Library for testing.

### Running Tests

To run all tests:

```bash
pnpm test
```

To run only utility tests (stable):

```bash
pnpm test:utils  # uses jest.config.simple.mjs (Node env)
```

To run tests in watch mode (useful during development):

```bash
pnpm test:watch
```

To generate a coverage report:

```bash
pnpm test:coverage
```

### Testing Status

Currently, we have implemented tests for:

- Utility functions (validation, etc.)

Component tests are still in progress due to compatibility issues with React 19 and testing libraries.

### Writing Tests

- Place test files next to the component or utility they test with a `.test.tsx` or `.test.ts` extension
- Alternatively, place tests in `__tests__` directories next to the files they test

Example test:

```tsx
import { render, screen } from '@testing-library/react';
import YourComponent from '../YourComponent';

describe('YourComponent', () => {
  test('renders correctly', () => {
    render(<YourComponent />);
    expect(screen.getByText('Your Text')).toBeInTheDocument();
  });
});
```

## API Type Generation

This project uses [@hey-api/openapi-ts](https://heyapi.dev/) to auto-generate TypeScript types and SDK functions from the backend's OpenAPI schema.

### Regenerating Types

When the backend API changes (new routes, modified schemas, etc.), regenerate the types:

```bash
# Backend must be running on port 8005
pnpm openapi:refresh
```

This command:
1. Fetches the OpenAPI schema from `http://localhost:8005/openapi.json`
2. Generates TypeScript types and SDK functions in `src/client/`

### Using Generated Types

```tsx
// Import types
import type { ContentOut, TemplateOut } from "@/client";

// Import SDK functions
import { getUserProfileUserProfileGet } from "@/client/sdk.gen";

// SDK functions return { data, error }
const { data, error } = await getUserProfileUserProfileGet();
```

### Important Notes

- **Never manually edit files in `src/client/`** - they are auto-generated
- **Wrapper functions** in `src/lib/apiWrappers.ts` provide simpler signatures for common operations
- **Generated files are excluded from Biome linting** (configured in `biome.json`)

## Building for Production

Build the application for production:

```bash
pnpm build
```

Start the production server:

```bash
pnpm start
```

## Docker

A Dockerfile is provided to build and run the application in a container:

```bash
# Build the Docker image
docker build -t morphio-frontend .

# Run the container
docker run -p 3005:3005 morphio-frontend
```

## Project Structure

```
frontend/
├── public/          # Static assets
├── src/
│   ├── app/         # Next.js App Router pages
│   ├── client/      # Auto-generated API types and SDK (DO NOT EDIT)
│   ├── components/  # React components
│   ├── constants/   # Application constants
│   ├── contexts/    # React contexts
│   ├── hooks/       # Custom React hooks
│   ├── lib/         # Utility libraries
│   ├── store/       # Global state management
│   └── utils/       # Helper functions
└── ...configuration files
```

## License

This project is proprietary and confidential. All rights reserved.
