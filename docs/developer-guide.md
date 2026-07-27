# Developer Guide

## Getting Started

### Prerequisites

- Node.js 22+
- npm 10+
- Supabase account with a project

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/pix-technologies.git
cd pix-technologies

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Start development
npm run dev
```

## Project Structure

```
pix-technologies/
├── src/                    # Frontend application
│   ├── components/         # UI components
│   │   ├── layout/         # Shell, sidebar, header
│   │   └── ui/             # Primitives
│   ├── lib/                # Utilities
│   │   └── supabase/       # Client, types, helpers
│   ├── pages/              # 18 route pages
│   ├── routes/             # Route definitions
│   ├── services/           # Database service layer
│   └── main.tsx            # Entry point
├── packages/
│   ├── agents/             # AI agent suite (8 agents)
│   └── services/           # Backend services (12 modules)
├── supabase/               # Database setup
├── docs/                   # Documentation
└── .github/workflows/      # CI/CD
```

## Key Scripts

| Command               | Description                        |
| --------------------- | ---------------------------------- |
| `npm run dev`         | Start frontend dev server          |
| `npm run build`       | Build frontend for production      |
| `npm run build:all`   | Build all workspace packages       |
| `npm test`            | Run all tests                      |
| `npm run typecheck`   | TypeScript type checking           |
| `npm run lint`        | Lint with oxlint                   |
| `npm run db:generate` | Regenerate Supabase types          |
| `npm run deploy`      | Build + deploy to Cloudflare Pages |

## Adding a Page

1. Create a component in `src/pages/`
2. Add route in `src/routeTree.tsx`
3. Add navigation item in `src/components/layout/Sidebar.tsx`

## Adding a Database Method

1. Add the method to `src/services/database.service.ts` using the `supabase` client
2. The method automatically uses the current organization context via `getCurrentOrgId()`

## Working with Agents

```typescript
// Create a new agent
import { BaseAgent } from "./base";

export class MyAgent extends BaseAgent {
  getName(): string {
    return "my-agent";
  }
  async run(context: AgentContext): Promise<AgentOutput> {
    // Implementation
    return { type: "my-type", data: {} };
  }
}
```

Register the agent in `AgentOrchestrator.registerAgents()` in `orchestrator.ts`.

## Testing

```bash
# Run all tests
npm test

# Run specific package tests
npm run test -w packages/agents
npm run test -w packages/services
```

## Docker

```bash
# Build and start all services
docker compose up --build

# Or run frontend only
docker build -t pix-frontend -f Dockerfile .
docker run -p 80:80 pix-frontend
```
