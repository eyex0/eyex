# πX Technologies - AI Backend

This is the backend for the πX Technologies platform. It's a Python-based application built with FastAPI that powers the AI agents, business intelligence, and data processing capabilities of πX.

## Technologies Used

- **Framework:** FastAPI
- **AI Framework:** LangGraph for agent orchestration
- **Database:** PostgreSQL (with Alembic for migrations)
- **Caching:** Redis
- **Authentication:** Supabase Auth (via JWT)
- **Deployment:** Docker

## Project Structure

The backend is organized into the following main directories:

-   `app/`: The main application code.
    -   `agents/`: Contains the LangGraph agent nodes.
    -   `api/`: Defines the RESTful API endpoints.
    -   `core/`: Core components like security, middleware, and configuration.
    -   `db/`: Database-related code, including models and migrations.
    -   `models/`: SQLAlchemy ORM models.
    -   `schemas/`: Pydantic schemas for data validation.
    -   `services/`: Business logic and services.
-   `tests/`: The pytest test suite.
-   `scripts/`: Utility scripts.
-   `alembic/`: Database migration scripts.

## Getting Started

### Prerequisites

-   Python (v3.12 or higher)
-   Docker and Docker Compose
-   A running PostgreSQL and Redis instance.

### Installation & Setup

1.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up environment variables:**

    Copy `.env.example` to `.env` and fill in the required values for `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, and `APP_SECRET_KEY`.

3.  **Run database migrations:**

    ```bash
    alembic upgrade head
    ```

## Running the Application

You can run the backend using Docker Compose:

```bash
docker-compose up --build
```

Alternatively, you can run it directly with Uvicorn for development:

```bash
uvicorn app.main:app --reload --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

## Testing

To run the test suite, use pytest:

```bash
pytest
```
