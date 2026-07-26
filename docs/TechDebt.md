# EyeX Technologies - Technical Debt

This document outlines the identified technical debt in the EyeX Technologies codebase.

## Frontend

-   **Use of `any` type:** The frontend codebase has a significant amount of `any` types. This reduces the benefits of using TypeScript and can lead to runtime errors. These should be replaced with more specific types.
-   **Styling inconsistencies:** While the project uses Tailwind CSS and has a defined color scheme, there are some inconsistencies in the application of styles. For example, some components use hardcoded colors instead of the defined tokens.
-   **Lack of tests:** The frontend has no unit or integration tests. This makes it difficult to refactor code or add new features without risking regressions.

## Backend

-   **Lack of tests:** While the backend has a good number of tests, the test coverage could be improved. There are still some parts of the code that are not covered by tests.
-   **`pix-technologies` directory:** There is a directory named `pix-technologies` at the root of the project that seems to be a separate Python project. It's not clear what its purpose is or if it's still in use. This should be investigated and either integrated into the main backend or removed.

## Documentation

-   **API Documentation:** The backend has a FastAPI interface, which automatically generates OpenAPI documentation. However, many endpoints lack detailed descriptions and examples.
-   **Component Documentation:** There is no documentation for the reusable UI components in the frontend. This makes it difficult for new developers to understand how to use them.

## General

-   **Environment variable management:** The project relies on `.env` files for managing environment variables. This is a good practice, but a more robust solution like a dedicated secret management service could be considered for production environments.
