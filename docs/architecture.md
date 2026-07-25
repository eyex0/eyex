# EyeX Technologies - System Architecture

This document provides a high-level overview of the system architecture of the EyeX Technologies platform.

## Overview

The EyeX platform is a full-stack application composed of a modern web frontend, a powerful AI-driven backend, and a robust data layer. The architecture is designed to be scalable, maintainable, and deployable in a containerized environment.

## Frontend

The frontend is a single-page application (SPA) built with **React** and **Vite**. It provides a rich and interactive user interface for interacting with the EyeX platform.

-   **Framework/Library:** React 19
-   **Build Tool:** Vite
-   **Language:** TypeScript
-   **Styling:** Tailwind CSS with shadcn/ui components
-   **Routing:** TanStack Router for client-side routing
-   **Data Fetching:** TanStack Query for managing server state

The frontend is served as a static asset build and is intended to be deployed behind a web server like Nginx.

## Backend

The backend is a Python-based application that provides the core business logic, AI capabilities, and API for the platform.

-   **Framework:** FastAPI, a modern, high-performance web framework for building APIs with Python.
-   **AI Orchestration:** LangGraph is used to create and manage complex, stateful, multi-agent AI workflows.
-   **AI Integration:** The backend integrates with Google Gemini via the `langchain-openai` library.
-   **Database Interaction:** SQLAlchemy is used as the Object-Relational Mapper (ORM) for interacting with the PostgreSQL database.
-   **Database Migrations:** Alembic is used for managing database schema migrations.
-   **Asynchronous Operations:** The backend is built to be fully asynchronous, leveraging Python's `asyncio` capabilities.

## Data Layer

The data layer consists of a PostgreSQL database for persistent storage and a Redis instance for caching and short-term data storage.

-   **Database:** PostgreSQL 16
-   **Caching:** Redis 7

Both the database and the cache are managed as services within the Docker Compose setup.

## Authentication

Authentication is handled by **Supabase Auth**. The frontend uses the `supabase-js` library to interact with Supabase for user authentication (signup, login, etc.). The backend verifies JWTs issued by Supabase to authenticate API requests.

## Deployment

The entire application is designed to be deployed using **Docker**. A `docker-compose.yml` file is provided to orchestrate the deployment of the frontend, backend, PostgreSQL database, and Redis cache.

The presence of a `wrangler.jsonc` file also suggests a potential deployment target of Cloudflare Workers, likely for server-side rendering (SSR) or edge functions.
