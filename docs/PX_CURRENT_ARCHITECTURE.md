# πX - Current System Architecture

This document provides a detailed overview of the current system architecture of the πX platform.

## 1. High-Level Overview

The πX platform is a full-stack application designed as a **Cognitive Operating Layer for Enterprises**. It consists of three main parts:

-   A **React-based web frontend** for user interaction.
-   A **Python-based backend** that provides the core AI and business logic.
-   A **data layer** consisting of a PostgreSQL database and a Redis cache.

The entire platform is designed to be containerized and deployed with Docker.

## 2. Frontend Architecture

The frontend is a modern single-page application (SPA) that provides the user interface for the πX platform.

-   **Framework:** React 19 with Vite.
-   **Language:** TypeScript.
-   **Styling:** Tailwind CSS with a custom theme and shadcn/ui components.
-   **Routing:** TanStack Router is used for client-side routing. All routes are defined in the `src/routes` directory.
-   **State Management:** TanStack Query is used for managing server state, caching, and data fetching. Client-side state is managed with React's built-in state management (useState, useContext).
-   **UI Architecture:** The UI is built around a component-based architecture. Reusable components are located in the `src/components` directory. The main layout is defined by the `AppShell` component.

## 3. Backend Architecture

The backend is the core of the πX platform, providing the AI capabilities and the API for the frontend.

-   **Framework:** FastAPI, a high-performance Python web framework.
-   **APIs:** The backend exposes a RESTful API for the frontend to consume. The API is organized into versioned endpoints under `/api/v1`.
-   **Services:** Business logic is encapsulated in services, which are located in the `pix-backend/app/services` directory.
-   **Database:** The backend uses **PostgreSQL** as its primary database. **SQLAlchemy** is used as the ORM, and **Alembic** is used for database migrations.
-   **Authentication:** The backend uses Supabase for user authentication. It validates JWTs issued by Supabase to secure its endpoints.
-   **Storage:** While the primary database is PostgreSQL, **Redis** is used for caching and short-term data storage.

## 4. AI Architecture

The AI capabilities of πX are built around a multi-agent system orchestrated by LangGraph.

-   **AI Models:** The platform uses Google's **Gemini** models for its AI capabilities, accessed via the `@google/genai` and `langchain-openai` libraries.
-   **Prompt Systems:** Each AI agent has a a well-defined system prompt that instructs it on its role, responsibilities, and output format. These prompts are located in the agent files in `pix-backend/app/agents`.
-   **RAG Implementation:** The platform uses a Retrieval-Augmented Generation (RAG) system.
    -   **Vector Memory:** A `VectorMemory` class in `packages/cognitive-kernel/memory-engine/vector_memory.py` provides an in-memory vector store using `sentence-transformers` for embeddings.
    -   **Knowledge Graph:** A `KnowledgeGraph` class in `packages/cognitive-kernel/knowledge-graph/main.py` provides an in-memory knowledge graph for storing business context.
-   **AI Workflows:** **LangGraph** is used to define and execute complex, multi-agent workflows. The `AgentGraph` in `packages/cognitive-kernel/workflow-engine/main.py` defines the relationships and transitions between the different AI agents. The primary workflows are:
    -   **Intelligence Workflow:** Analyst → Strategist → Decision
    -   **Executive Workflow:** CEO → CFO → COO → Risk
    -   **Engineering Workflow:** Planner → Researcher → Coder → Reviewer → Tester → Documenter → DevOps

## 5. Infrastructure

-   **Deployment:** The application is designed to be deployed using **Docker Compose**. A `docker-compose.yml` file is provided to orchestrate the deployment of the frontend, backend, PostgreSQL database, and Redis cache. The `Dockerfile.api` and `Dockerfile` are used to build the backend and frontend images, respectively.
-   **Environment Variables:** The application uses `.env` files for managing environment variables. The `pydantic-settings` library is used in the backend to manage configuration.
-   **Security:**
    -   Authentication is handled by Supabase.
    -   Row Level Security (RLS) is enabled on all database tables to ensure data isolation between organizations.
    -   The backend includes security middleware for headers, CORS, and rate limiting.

## 6. List of Pages, APIs, Components, Routes, and Database Tables

This information is extensive and is better suited for separate, more detailed documents. High-level summaries are provided here.

-   **Pages:** The application has over 20 pages, including authentication pages, a dashboard, and pages for each business domain (CRM, Sales, Finance, etc.).
-   **APIs:** The backend exposes a rich set of APIs for interacting with the platform's features, including AI agents, data sources, and business modules.
-   **Components:** The frontend has a well-organized component library with reusable UI components for various purposes.
-   **Routes:** All frontend routes are defined in the `src/routes` directory and managed by TanStack Router.
-   **Database Tables:** The database consists of over 25 tables, covering core concepts like organizations and users, as well as business domains like finance, CRM, and HR.
