# EyeX Technologies - File Structure

This document outlines the file and directory structure of the EyeX Technologies platform.

## Root Directory

The root directory contains the configuration files for the frontend, Docker, and other project-level settings.

-   `.github/`: Contains GitHub Actions workflows for CI/CD.
-   `docs/`: Contains project documentation.
-   `pix-backend/`: The Python backend application.
-   `pix-technologies/`: Seems to be a separate, but related, Python project.
-   `public/`: Public assets for the frontend.
-   `scripts/`: Utility scripts for the project.
-   `src/`: The source code for the React frontend application.
-   `supabase/`: SQL scripts for setting up the Supabase database.
-   `package.json`: Defines the frontend dependencies and scripts.
-   `vite.config.ts`: Vite configuration for the frontend.
-   `docker-compose.yml`: Docker Compose file for orchestrating the services.
-   `Dockerfile`: Dockerfile for the frontend.

## Frontend (`src/`)

The `src` directory contains the source code for the React frontend application.

-   `agents/`: Contains code related to the AI agents on the frontend.
-   `components/`: Reusable UI components.
    -   `auth/`: Components related to authentication.
    -   `common/`: Common, primitive components.
    -   `layout/`: Components that define the layout of the application (e.g., `AppShell`, `SiteHeader`).
    -   `providers/`: React context providers (e.g., `AuthProvider`).
    -   `ui/`: Generic UI components, likely from a UI library like shadcn/ui.
-   `hooks/`: Custom React hooks.
-   `lib/`: Utility functions and libraries.
    -   `supabase/`: Supabase client and type definitions.
-   `pages/`: The main pages of the application.
-   `routes/`: Route definitions for TanStack Router.
-   `services/`: Services for interacting with the backend API.
-   `main.tsx`: The entry point of the React application.
-   `router.tsx`: The main router configuration.
-   `routeTree.gen.ts`: A generated file for TanStack Router that contains the route tree.
-   `styles.css`: Global CSS styles.

## Backend (`pix-backend/`)

The `pix-backend` directory contains the source code for the Python backend application.

-   `app/`: The main application code.
    -   `agents/`: Contains the LangGraph agent nodes.
    -   `api/`: Defines the RESTful API endpoints.
    -   `core/`: Core components like security, middleware, and configuration.
    -   `db/`: Database-related code, including models and migrations.
    -   `models/`: SQLAlchemy ORM models.
    -   `schemas/`: Pydantic schemas for data validation.
    -   `services/`: Business logic and services.
-   `tests/`: The pytest test suite.
-   `scripts/`: Utility scripts for the backend.
-   `alembic/`: Database migration scripts.
-   `pyproject.toml`: Defines the backend dependencies and project settings.
-   `Dockerfile.prod`: Dockerfile for the production backend image.
