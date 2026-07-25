# EyeX Technologies - Database Schema

This document provides an overview of the PostgreSQL database schema used by the EyeX Technologies platform.

## Tables

The database is composed of several tables, organized by business domain.

### Core Tables

-   **organizations**: Stores information about the organizations using the platform.
    -   `id` (UUID, PK)
    -   `name` (TEXT)
    -   `slug` (TEXT, UNIQUE)
    -   `logo_url` (TEXT)
    -   `plan` (TEXT)
    -   `created_at` (TIMESTAMPTZ)
    -   `updated_at` (TIMESTAMPTZ)
-   **profiles**: Extends the `auth.users` table with user profile information.
    -   `id` (UUID, PK, FK to `auth.users.id`)
    -   `email` (TEXT)
    -   `full_name` (TEXT)
    -   `avatar_url` (TEXT)
    -   `role` (TEXT)
    -   `organization_id` (UUID, FK to `organizations.id`)
    -   `created_at` (TIMESTAMPTZ)
    -   `updated_at` (TIMESTAMPTZ)
-   **org_members**: A junction table that links users to organizations.
    -   `id` (UUID, PK)
    -   `organization_id` (UUID, FK to `organizations.id`)
    -   `user_id` (UUID, FK to `auth.users.id`)
    -   `role` (TEXT)
    -   `created_at` (TIMESTAMPTZ)

### Finance

-   **finance_invoices**: Stores invoice data.
-   **finance_budgets**: Stores budget data.
-   **finance_transactions**: Stores financial transactions.

### CRM

-   **crm_customers**: Stores customer information.
-   **crm_leads**: Stores lead information.
-   **crm_deals**: Stores sales deal information.
-   **crm_activities**: Stores CRM-related activities.

### Sales

-   **sales_orders**: Stores sales order data.
-   **sales_products**: Stores product information.

### HR

-   **hr_employees**: Stores employee information.
-   **hr_departments**: Stores department information.
-   **hr_payroll**: Stores payroll data.

### Projects

-   **projects_projects**: Stores project information.
-   **projects_tasks**: Stores task information.

### Inventory

-   **inventory_warehouses**: Stores warehouse information.
-   **inventory_suppliers**: Stores supplier information.
-   **inventory_products**: Stores inventory product information.

### Other Tables

-   **documents**: Stores information about uploaded documents.
-   **notifications**: Stores user notifications.
-   **dashboards**: Stores dashboard configurations.
-   **data_sources**: Stores information about connected data sources.
-   **imported_datasets**: Stores data from imported datasets (e.g., CSV, Excel).
-   **import_mappings**: Stores mappings for imported datasets.
-   **contact_submissions**: Stores submissions from the public contact form.

## Row Level Security (RLS)

Row Level Security is enabled on all tables to ensure data privacy and isolation between organizations. Policies are in place to restrict access to data based on the user's organization membership.

## Functions and Triggers

-   **`auth.user_org_id()`**: A helper function to get the current user's organization ID.
-   **`auth.is_org_member(org_id UUID)`**: A helper function to check if the current user is a member of the specified organization.
-   **`public.handle_new_user()`**: A trigger function that automatically creates a new organization and profile for a new user upon signup.
-   **`public.ensure_organization(p_slug TEXT, p_name TEXT)`**: An RPC function to ensure an organization exists.
