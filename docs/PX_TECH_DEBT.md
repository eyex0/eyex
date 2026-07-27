# πX - Technical Debt

This document outlines the identified technical debt in the πX codebase. This list is not exhaustive, but it captures the most significant areas for improvement.

## Frontend

### 1. Lack of Automated Testing
-   **Debt:** The frontend has no unit or integration tests.
-   **Impact:** This makes it difficult to refactor code or add new features without risking regressions. It also slows down the development process, as manual testing is required for all changes.
-   **Recommendation:** Implement a testing strategy using a framework like Vitest and React Testing Library. Start by adding tests for critical components and user flows, such as authentication and core business logic.

### 2. Inconsistent Type Safety
-   **Debt:** The frontend codebase has a significant amount of `any` types.
-   **Impact:** This reduces the benefits of using TypeScript, such as static type checking and improved developer experience. It can also lead to runtime errors that could have been caught at compile time.
-   **Recommendation:** Gradually replace `any` types with more specific types. Enable stricter TypeScript compiler options to enforce better type safety.

### 3. Styling Inconsistencies
-   **Debt:** While the project uses Tailwind CSS and has a defined color scheme, there are some inconsistencies in the application of styles. For example, some components use hardcoded color values instead of the defined tokens.
-   **Impact:** This can lead to an inconsistent UI and makes it difficult to maintain and update the visual design of the application.
-   **Recommendation:** Perform a full audit of the CSS and component styles to ensure that all colors, fonts, and spacing are using the defined Tailwind theme.

## Backend

### 1. Incomplete Test Coverage
-   **Debt:** While the backend has a good number of tests, the test coverage is not complete. There are still some parts of the code that are not covered by tests.
-   **Impact:** This increases the risk of regressions when making changes to the codebase.
-   **Recommendation:** Increase test coverage, especially for critical business logic and API endpoints. Aim for a coverage of at least 80%.

### 2. Unclear Purpose of `pix-technologies` Directory
-   **Debt:** There is a directory named `pix-technologies` at the root of the project that seems to be a separate Python project. It's not clear what its purpose is or if it's still in use.
-   **Impact:** This can create confusion for new developers and adds unnecessary complexity to the project structure.
-   **Recommendation:** Investigate the purpose of this directory. If it's no longer needed, it should be removed. If it is needed, it should be properly documented and integrated into the main project.

### 3. Lack of Detailed API Documentation
-   **Debt:** The backend has a FastAPI interface, which automatically generates OpenAPI documentation. However, many endpoints lack detailed descriptions, examples, and documentation for their request and response models.
-   **Impact:** This makes it difficult for frontend developers and external API consumers to understand and use the API.
-   **Recommendation:** Add detailed descriptions and examples to all API endpoints and their associated Pydantic models.

## AI

### 1. In-Memory Vector Store
-   **Debt:** The current RAG implementation uses an in-memory vector store.
-   **Impact:** This is not a scalable solution for a production environment. The vector store will be lost if the application restarts, and it cannot be shared across multiple instances of the backend.
-   **Recommendation:** Replace the in-memory vector store with a persistent and scalable solution like a dedicated vector database (e.g., Pinecone, Weaviate) or a PostgreSQL extension like `pgvector`.

## General

### 1. Environment Variable Management
-   **Debt:** The project relies on `.env` files for managing environment variables.
-   **Impact:** While this is acceptable for local development, it's not a secure or scalable solution for production environments.
-   **Recommendation:** Use a dedicated secret management service like HashiCorp Vault, AWS Secrets Manager, or Doppler to manage secrets and environment variables in production.
