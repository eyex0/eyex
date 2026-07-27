-- πX Technologies — Enterprise Tables Migration
-- Migration 001: Add missing enterprise, AI, and data intelligence tables
-- Also fixes RLS policies from open (true) to proper org-scoped access

-- ============================================================
-- 1. EXTEND imported_datasets with missing columns
-- ============================================================
ALTER TABLE imported_datasets 
  ADD COLUMN IF NOT EXISTS file_size bigint,
  ADD COLUMN IF NOT EXISTS file_type text,
  ADD COLUMN IF NOT EXISTS storage_path text,
  ADD COLUMN IF NOT EXISTS processing_progress integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS organization_id uuid REFERENCES organizations(id) ON DELETE CASCADE;

-- ============================================================
-- 2. WORKSPACES TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  is_default boolean NOT NULL DEFAULT false,
  settings jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(organization_id, slug)
);

-- ============================================================
-- 3. AGENT_CONFIGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  agent_role text NOT NULL,
  display_name text NOT NULL,
  description text,
  is_enabled boolean NOT NULL DEFAULT true,
  model text,
  temperature numeric(3,2),
  max_tokens integer,
  config jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, agent_role)
);

-- ============================================================
-- 4. TASK_EXECUTIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS task_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  session_id text,
  agent_role text,
  input_text text,
  output_text text,
  status text NOT NULL DEFAULT 'pending',
  duration_ms integer,
  steps jsonb,
  error text,
  tokens_used integer,
  cost numeric(10,6),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 5. API_KEYS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name text NOT NULL,
  key_hash text NOT NULL,
  key_prefix text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  last_used_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 6. WORKSPACE_MEMBERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS workspace_members (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'member',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, user_id)
);

-- ============================================================
-- 7. AUDIT_LOGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  action text NOT NULL,
  resource_type text,
  resource_id text,
  metadata jsonb,
  ip_address text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 8. COMPANY_MEMORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS company_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  key text NOT NULL,
  value text NOT NULL,
  category text DEFAULT 'general',
  created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(organization_id, key)
);

-- ============================================================
-- 9. MISSIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS missions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  workspace_id uuid REFERENCES workspaces(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'pending',
  priority text DEFAULT 'medium',
  assigned_agents text[],
  result jsonb,
  created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 10. SUBSCRIPTION_PLANS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text NOT NULL UNIQUE,
  description text,
  price_monthly numeric(10,2) NOT NULL DEFAULT 0,
  price_yearly numeric(10,2) NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'USD',
  max_users integer NOT NULL DEFAULT 5,
  max_agents integer NOT NULL DEFAULT 3,
  max_tasks_per_month integer NOT NULL DEFAULT 100,
  features jsonb,
  is_active boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- 11. SUBSCRIPTIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES subscription_plans(id),
  status text NOT NULL DEFAULT 'active',
  billing_interval text NOT NULL DEFAULT 'monthly',
  current_period_start timestamptz NOT NULL DEFAULT now(),
  current_period_end timestamptz,
  trial_end timestamptz,
  cancel_at_period_end boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(organization_id)
);

-- ============================================================
-- 12. INVOICES TABLE (billing)
-- ============================================================
CREATE TABLE IF NOT EXISTS billing_invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  amount numeric(10,2) NOT NULL,
  currency text NOT NULL DEFAULT 'USD',
  status text NOT NULL DEFAULT 'pending',
  description text,
  period_start timestamptz,
  period_end timestamptz,
  paid_at timestamptz,
  invoice_url text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_task_executions_workspace ON task_executions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions(status);
CREATE INDEX IF NOT EXISTS idx_task_executions_created ON task_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_company_memory_org ON company_memory(organization_id);
CREATE INDEX IF NOT EXISTS idx_missions_org ON missions(organization_id);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
CREATE INDEX IF NOT EXISTS idx_workspaces_org ON workspaces(organization_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX IF NOT EXISTS idx_imported_datasets_org ON imported_datasets(organization_id);

-- ============================================================
-- UPDATED_AT TRIGGERS
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_workspaces_updated_at') THEN
    CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_task_executions_updated_at') THEN
    CREATE TRIGGER update_task_executions_updated_at BEFORE UPDATE ON task_executions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_missions_updated_at') THEN
    CREATE TRIGGER update_missions_updated_at BEFORE UPDATE ON missions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_company_memory_updated_at') THEN
    CREATE TRIGGER update_company_memory_updated_at BEFORE UPDATE ON company_memory FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_agent_configs_updated_at') THEN
    CREATE TRIGGER update_agent_configs_updated_at BEFORE UPDATE ON agent_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_subscriptions_updated_at') THEN
    CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;

-- ============================================================
-- ENABLE RLS ON NEW TABLES
-- ============================================================
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_invoices ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- RLS POLICIES — NEW TABLES (proper org-scoped access)
-- ============================================================

-- Workspaces: members of the org can access
CREATE POLICY "workspace_org_access" ON workspaces FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Agent configs: workspace members can access
CREATE POLICY "agent_configs_workspace_access" ON agent_configs FOR ALL USING (
  workspace_id IN (
    SELECT w.id FROM workspaces w
    JOIN organization_members om ON om.organization_id = w.organization_id
    WHERE om.user_id = auth.uid()
  )
);

-- Task executions: workspace members can access
CREATE POLICY "task_executions_workspace_access" ON task_executions FOR ALL USING (
  workspace_id IN (
    SELECT w.id FROM workspaces w
    JOIN organization_members om ON om.organization_id = w.organization_id
    WHERE om.user_id = auth.uid()
  )
);

-- API Keys: workspace members can access
CREATE POLICY "api_keys_workspace_access" ON api_keys FOR ALL USING (
  workspace_id IN (
    SELECT w.id FROM workspaces w
    JOIN organization_members om ON om.organization_id = w.organization_id
    WHERE om.user_id = auth.uid()
  )
);

-- Workspace members: members can view, owners can manage
CREATE POLICY "workspace_members_view" ON workspace_members FOR SELECT USING (
  workspace_id IN (
    SELECT w.id FROM workspaces w
    JOIN organization_members om ON om.organization_id = w.organization_id
    WHERE om.user_id = auth.uid()
  )
);

-- Audit logs: org members can view their org logs
CREATE POLICY "audit_logs_org_access" ON audit_logs FOR SELECT USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Company memory: org members can access
CREATE POLICY "company_memory_org_access" ON company_memory FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Missions: org members can access
CREATE POLICY "missions_org_access" ON missions FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Subscription plans: everyone can read
CREATE POLICY "subscription_plans_public_read" ON subscription_plans FOR SELECT USING (true);

-- Subscriptions: org members can view their subscription
CREATE POLICY "subscriptions_org_access" ON subscriptions FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Billing invoices: org members can view via subscription
CREATE POLICY "billing_invoices_org_access" ON billing_invoices FOR SELECT USING (
  subscription_id IN (
    SELECT s.id FROM subscriptions s
    JOIN organization_members om ON om.organization_id = s.organization_id
    WHERE om.user_id = auth.uid()
  )
);

-- ============================================================
-- FIX EXISTING RLS POLICIES (replace open 'true' with org-scoped)
-- ============================================================

-- Fix organizations RLS
DROP POLICY IF EXISTS "org_access" ON organizations;
CREATE POLICY "organizations_member_access" ON organizations FOR ALL USING (
  id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix profiles RLS
DROP POLICY IF EXISTS "org_access" ON profiles;
CREATE POLICY "profiles_own_access" ON profiles FOR ALL USING (
  id = auth.uid() OR
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix org_members RLS
DROP POLICY IF EXISTS "org_access" ON org_members;
CREATE POLICY "org_members_access" ON org_members FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix data_sources RLS
DROP POLICY IF EXISTS "org_access" ON data_sources;
CREATE POLICY "data_sources_org_access" ON data_sources FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix dashboards RLS
DROP POLICY IF EXISTS "org_access" ON dashboards;
CREATE POLICY "dashboards_org_access" ON dashboards FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix documents RLS
DROP POLICY IF EXISTS "org_access" ON documents;
CREATE POLICY "documents_org_access" ON documents FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix notifications RLS
DROP POLICY IF EXISTS "org_access" ON notifications;
CREATE POLICY "notifications_org_access" ON notifications FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix CRM tables RLS
DROP POLICY IF EXISTS "org_access" ON crm_customers;
CREATE POLICY "crm_customers_org_access" ON crm_customers FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON crm_deals;
CREATE POLICY "crm_deals_org_access" ON crm_deals FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON crm_leads;
CREATE POLICY "crm_leads_org_access" ON crm_leads FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON crm_activities;
CREATE POLICY "crm_activities_org_access" ON crm_activities FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix Finance tables RLS
DROP POLICY IF EXISTS "org_access" ON finance_invoices;
CREATE POLICY "finance_invoices_org_access" ON finance_invoices FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON finance_transactions;
CREATE POLICY "finance_transactions_org_access" ON finance_transactions FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON finance_budgets;
CREATE POLICY "finance_budgets_org_access" ON finance_budgets FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix HR tables RLS
DROP POLICY IF EXISTS "org_access" ON hr_employees;
CREATE POLICY "hr_employees_org_access" ON hr_employees FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON hr_departments;
CREATE POLICY "hr_departments_org_access" ON hr_departments FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON hr_payroll;
CREATE POLICY "hr_payroll_org_access" ON hr_payroll FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix Inventory tables RLS
DROP POLICY IF EXISTS "org_access" ON inventory_products;
CREATE POLICY "inventory_products_org_access" ON inventory_products FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON inventory_warehouses;
CREATE POLICY "inventory_warehouses_org_access" ON inventory_warehouses FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON inventory_suppliers;
CREATE POLICY "inventory_suppliers_org_access" ON inventory_suppliers FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix Projects tables RLS
DROP POLICY IF EXISTS "org_access" ON projects_projects;
CREATE POLICY "projects_projects_org_access" ON projects_projects FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON projects_tasks;
CREATE POLICY "projects_tasks_org_access" ON projects_tasks FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix Sales tables RLS
DROP POLICY IF EXISTS "org_access" ON sales_orders;
CREATE POLICY "sales_orders_org_access" ON sales_orders FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON sales_products;
CREATE POLICY "sales_products_org_access" ON sales_products FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- Fix Import tables RLS
DROP POLICY IF EXISTS "org_access" ON import_mappings;
CREATE POLICY "import_mappings_org_access" ON import_mappings FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "org_access" ON imported_datasets;
CREATE POLICY "imported_datasets_org_access" ON imported_datasets FOR ALL USING (
  organization_id IN (
    SELECT organization_id FROM organization_members WHERE user_id = auth.uid()
  )
);

-- ============================================================
-- SEED DEFAULT SUBSCRIPTION PLANS
-- ============================================================
INSERT INTO subscription_plans (name, slug, description, price_monthly, price_yearly, max_users, max_agents, max_tasks_per_month, sort_order, is_active)
VALUES
  ('Starter', 'starter', 'Perfect for small teams getting started with AI', 49.00, 490.00, 5, 3, 500, 1, true),
  ('Professional', 'professional', 'Advanced AI capabilities for growing businesses', 149.00, 1490.00, 20, 10, 2000, 2, true),
  ('Enterprise', 'enterprise', 'Full AI Operating System for large organizations', 499.00, 4990.00, 100, 50, 10000, 3, true)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- AUTO-PROVISION DEFAULT WORKSPACE FOR NEW ORGANIZATIONS
-- ============================================================
CREATE OR REPLACE FUNCTION auto_provision_workspace()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO workspaces (organization_id, name, slug, is_default)
  VALUES (NEW.id, 'Default Workspace', 'default', true)
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_organization_created ON organizations;
CREATE TRIGGER on_organization_created
  AFTER INSERT ON organizations
  FOR EACH ROW EXECUTE FUNCTION auto_provision_workspace();
