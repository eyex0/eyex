# EyeX Technologies

**EyeX Technologies** is an AI-powered enterprise decision intelligence platform. It acts as a virtual executive team, analyzing company data to identify risks and opportunities, and providing strategic recommendations through natural language interaction.

## Key Features

- **AI Executive Team:** A collaborative multi-agent system (CEO, CFO, COO, Risk) built with LangGraph.
- **Company Memory System:** A knowledge graph with vector embeddings for deep contextual understanding.
- **Proactive Intelligence:** Automatically detects risks, opportunities, and knowledge gaps in your business data.
- **Secure and Isolated:** Enterprise-grade data isolation for each organization.
- **Data Connectors:** Ingest data from various sources, including files, APIs, and databases.

## Technologies Used

- **Frontend:** React (with Vite), TypeScript, Tailwind CSS, shadcn/ui, TanStack Router
- **Backend:** Python, FastAPI, LangGraph
- **Data Layer:** Supabase (PostgreSQL), Redis
- **AI:** Google Gemini

## Getting Started

### Prerequisites

- Node.js (v20 or higher)
- Python (v3.12 or higher)
- Docker and Docker Compose
- Supabase account and project

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/eyex-technologies/eyex.git
    cd eyex
    ```

2.  **Set up environment variables:**

    -   **Frontend:** Copy `.env.example` to `.env` and fill in the required values for `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
    -   **Backend:** In the `eyex-backend` directory, copy `.env.example` to `.env` and provide the necessary credentials for `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, and `APP_SECRET_KEY`.

3.  **Install dependencies:**

    ```bash
    # For the frontend
    npm install

    # For the backend
    pip install -r eyex-backend/requirements.txt
    ```

## Running the Application

1.  **Start the backend:**

    Navigate to the `eyex-backend` directory and run:

    ```bash
    docker-compose up --build
    ```

    The backend API will be available at `http://localhost:8000`.

2.  **Start the frontend:**

    In the root directory, run:

    ```bash
    npm run dev
    ```

    The application will be accessible at `http://localhost:5173`.
