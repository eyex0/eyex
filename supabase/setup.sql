-- Run this entire script in Supabase SQL Editor to set up all tables + RLS + seed data

-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Organizations
CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  logo_url TEXT,
  plan TEXT NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Profiles
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  role TEXT NOT NULL DEFAULT 'member',
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Org Members
CREATE TABLE IF NOT EXISTS org_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(organization_id, user_id)
);

-- 4. Finance: Invoices
CREATE TABLE IF NOT EXISTS finance_invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  invoice_number TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  due_date DATE NOT NULL,
  issued_date DATE NOT NULL DEFAULT CURRENT_DATE,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Finance: Budgets
CREATE TABLE IF NOT EXISTS finance_budgets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  department TEXT NOT NULL,
  category TEXT NOT NULL,
  allocated DECIMAL(12,2) NOT NULL,
  spent DECIMAL(12,2) NOT NULL DEFAULT 0,
  period TEXT NOT NULL,
  fiscal_year INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Finance: Transactions
CREATE TABLE IF NOT EXISTS finance_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('revenue','expense')),
  category TEXT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  description TEXT,
  transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. CRM: Customers
CREATE TABLE IF NOT EXISTS crm_customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  company TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  lifetime_value DECIMAL(12,2) NOT NULL DEFAULT 0,
  last_contacted TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. CRM: Leads
CREATE TABLE IF NOT EXISTS crm_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  source TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. CRM: Deals
CREATE TABLE IF NOT EXISTS crm_deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  value DECIMAL(12,2) NOT NULL,
  stage TEXT NOT NULL DEFAULT 'prospecting',
  probability INT NOT NULL DEFAULT 10,
  close_date DATE,
  customer_id UUID REFERENCES crm_customers(id) ON DELETE SET NULL,
  owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. CRM: Activities
CREATE TABLE IF NOT EXISTS crm_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  subject TEXT NOT NULL,
  description TEXT,
  related_to TEXT,
  related_id UUID,
  performed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 11. Sales: Orders
CREATE TABLE IF NOT EXISTS sales_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  order_number TEXT NOT NULL,
  customer_id UUID REFERENCES crm_customers(id) ON DELETE SET NULL,
  total DECIMAL(12,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  order_date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. Sales: Products
CREATE TABLE IF NOT EXISTS sales_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sku TEXT NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  cost DECIMAL(10,2),
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. HR: Employees
CREATE TABLE IF NOT EXISTS hr_employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  position TEXT NOT NULL,
  department_id UUID,
  salary DECIMAL(12,2) NOT NULL,
  hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. HR: Departments
CREATE TABLE IF NOT EXISTS hr_departments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  head_id UUID REFERENCES hr_employees(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add department FK to employees after departments exist
ALTER TABLE hr_employees DROP CONSTRAINT IF EXISTS hr_employees_department_id_fkey;
ALTER TABLE hr_employees ADD CONSTRAINT hr_employees_department_id_fkey FOREIGN KEY (department_id) REFERENCES hr_departments(id) ON DELETE SET NULL;

-- 15. HR: Payroll
CREATE TABLE IF NOT EXISTS hr_payroll (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  employee_id UUID NOT NULL REFERENCES hr_employees(id) ON DELETE CASCADE,
  salary DECIMAL(12,2) NOT NULL,
  bonuses DECIMAL(12,2) NOT NULL DEFAULT 0,
  deductions DECIMAL(12,2) NOT NULL DEFAULT 0,
  pay_period_start DATE NOT NULL,
  pay_period_end DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 16. Projects
CREATE TABLE IF NOT EXISTS projects_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'planning',
  priority TEXT NOT NULL DEFAULT 'medium',
  start_date DATE,
  end_date DATE,
  owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  budget DECIMAL(12,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 17. Tasks
CREATE TABLE IF NOT EXISTS projects_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects_projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  priority TEXT NOT NULL DEFAULT 'medium',
  assignee_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  due_date DATE,
  estimated_hours DECIMAL(6,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 18. Inventory: Warehouses
CREATE TABLE IF NOT EXISTS inventory_warehouses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  location TEXT,
  capacity INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 19. Inventory: Suppliers
CREATE TABLE IF NOT EXISTS inventory_suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact_name TEXT,
  email TEXT,
  phone TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 20. Inventory: Products
CREATE TABLE IF NOT EXISTS inventory_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sku TEXT NOT NULL,
  category TEXT,
  unit_price DECIMAL(10,2) NOT NULL,
  quantity INT NOT NULL DEFAULT 0,
  reorder_level INT NOT NULL DEFAULT 10,
  warehouse_id UUID REFERENCES inventory_warehouses(id) ON DELETE SET NULL,
  supplier_id UUID REFERENCES inventory_suppliers(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 21. Documents
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  file_url TEXT,
  file_type TEXT,
  size_bytes BIGINT,
  tags TEXT[],
  uploaded_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 22. Notifications
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'info',
  read BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 23. Dashboards
CREATE TABLE IF NOT EXISTS dashboards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  config JSONB NOT NULL DEFAULT '{}',
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 24. Data Sources
CREATE TABLE IF NOT EXISTS data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  config JSONB NOT NULL DEFAULT '{}',
  enabled BOOLEAN NOT NULL DEFAULT true,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 25. Imported Datasets (for Excel/CSV uploads)
CREATE TABLE IF NOT EXISTS imported_datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  original_filename TEXT,
  columns JSONB NOT NULL DEFAULT '[]',
  rows JSONB NOT NULL DEFAULT '[]',
  row_count INT NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  mapped_table TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 26. Import Mappings (column mapping configs)
CREATE TABLE IF NOT EXISTS import_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  dataset_id UUID REFERENCES imported_datasets(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  source_columns JSONB NOT NULL DEFAULT '[]',
  target_table TEXT NOT NULL,
  column_mapping JSONB NOT NULL DEFAULT '{}',
  transform_rules JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 27. Contact Submissions (public contact form)
CREATE TABLE IF NOT EXISTS contact_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  company TEXT,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_finance_invoices_org ON finance_invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_finance_transactions_org ON finance_transactions(organization_id);
CREATE INDEX IF NOT EXISTS idx_crm_customers_org ON crm_customers(organization_id);
CREATE INDEX IF NOT EXISTS idx_crm_leads_org ON crm_leads(organization_id);
CREATE INDEX IF NOT EXISTS idx_crm_deals_org ON crm_deals(organization_id);
CREATE INDEX IF NOT EXISTS idx_sales_orders_org ON sales_orders(organization_id);
CREATE INDEX IF NOT EXISTS idx_hr_employees_org ON hr_employees(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_projects_org ON projects_projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_tasks_project ON projects_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_inventory_products_org ON inventory_products(organization_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_org ON documents(organization_id);

-- RLS: Enable on all tables
DO $$ DECLARE
  tbl TEXT;
BEGIN
  FOR tbl IN
    SELECT unnest(ARRAY[
      'organizations','profiles','org_members',
      'finance_invoices','finance_budgets','finance_transactions',
      'crm_customers','crm_leads','crm_deals','crm_activities',
      'sales_orders','sales_products',
      'hr_employees','hr_departments','hr_payroll',
      'projects_projects','projects_tasks',
      'inventory_products','inventory_warehouses','inventory_suppliers',
      'documents','notifications','dashboards','data_sources',
      'contact_submissions',
      'imported_datasets','import_mappings'
    ])
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
  END LOOP;
END $$;

-- RLS Policies (organization-scoped: users can only access their org's data)
-- Helper: get the current user's organization_id
CREATE OR REPLACE FUNCTION auth.user_org_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
  SELECT organization_id FROM public.profiles WHERE id = auth.uid()
$$;

-- Helper: check if user belongs to the target organization
CREATE OR REPLACE FUNCTION auth.is_org_member(org_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.org_members
    WHERE organization_id = org_id AND user_id = auth.uid()
  )
$$;

-- Organizations: users can see their own org
CREATE POLICY "org_access" ON organizations
  FOR ALL USING (id = auth.user_org_id());

-- Profiles: users can see profiles in their org + their own profile
CREATE POLICY "org_access" ON profiles
  FOR ALL USING (
    id = auth.uid() OR
    organization_id = auth.user_org_id()
  );

-- Org members: users can see members of their orgs
CREATE POLICY "org_access" ON org_members
  FOR ALL USING (
    user_id = auth.uid() OR
    auth.is_org_member(organization_id)
  );

-- Business tables: scoped by organization_id
CREATE POLICY "org_access" ON finance_invoices
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON finance_budgets
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON finance_transactions
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON crm_customers
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON crm_leads
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON crm_deals
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON crm_activities
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON sales_orders
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON sales_products
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON hr_employees
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON hr_departments
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON hr_payroll
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON projects_projects
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON projects_tasks
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON inventory_products
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON inventory_warehouses
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON inventory_suppliers
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON documents
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON notifications
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON dashboards
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON data_sources
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON imported_datasets
  FOR ALL USING (auth.is_org_member(organization_id));
CREATE POLICY "org_access" ON import_mappings
  FOR ALL USING (auth.is_org_member(organization_id));

-- Contact submissions: anyone can insert (public form), only authed users can view
CREATE POLICY "insert_public" ON contact_submissions
  FOR INSERT WITH CHECK (true);
CREATE POLICY "select_authed" ON contact_submissions
  FOR SELECT USING (auth.role() = 'authenticated');

-- Auto-provisioning trigger: create org + profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
  org_id UUID;
BEGIN
  INSERT INTO public.organizations (name, slug)
  VALUES (COALESCE(NEW.raw_user_meta_data ->> 'organization_name', 'My Organization'),
          COALESCE(NEW.raw_user_meta_data ->> 'organization_slug', 'org-' || substr(NEW.id::text, 1, 8)))
  RETURNING id INTO org_id;

  INSERT INTO public.profiles (id, email, full_name, role, organization_id)
  VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data ->> 'full_name', NEW.email), 'owner', org_id);

  INSERT INTO public.org_members (organization_id, user_id, role)
  VALUES (org_id, NEW.id, 'owner');

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ensure_organization RPC (for client-side idempotent org access)
CREATE OR REPLACE FUNCTION public.ensure_organization(p_slug TEXT, p_name TEXT)
RETURNS SETOF public.organizations
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  RETURN QUERY
  INSERT INTO public.organizations (name, slug)
  VALUES (p_name, p_slug)
  ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
  RETURNING *;
END;
$$;

-- Seed data
DO $$
DECLARE
  org_id UUID;
BEGIN
  -- Ensure the default organization exists, but do not seed it with excessive data
  SELECT id INTO org_id FROM organizations WHERE slug = 'default-org';
  IF org_id IS NULL THEN
    INSERT INTO organizations (name, slug) VALUES ('Default Organization', 'default-org')
    RETURNING id INTO org_id;
  END IF;
END $$;

