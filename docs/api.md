# API Reference

## Database Service (`db`)

All data access goes through the `db` object from `src/services/database.service.ts`.

### Organization

```typescript
getOrganization(): Promise<Organization | null>
updateOrganization(input: { name?: string; slug?: string }): Promise<Organization>
getSubscription(): Promise<{ plan: string; status: string; currentPeriodEnd: string | null } | null>
```

### Users & Teams

```typescript
getUsers(filters?: { teamId?: string; role?: string }): Promise<User[]>
inviteUser(email: string, role: string, teamIds?: string[]): Promise<{ user: any; inviteSent: boolean }>
updateUserRole(userId: string, role: 'owner' | 'admin' | 'analyst' | 'viewer'): Promise<User>
removeUser(userId: string): Promise<void>
getProfiles(): Promise<any[]>
getTeams(): Promise<Team[]>
createTeam(input: { name: string; description?: string }): Promise<Team>
addTeamMembers(teamId: string, userIds: string[], role?: string): Promise<void>
```

### API Keys

```typescript
getApiKeys(): Promise<ApiKey[]>
createApiKey(input: { name: string; scopes: string[]; expiresAt?: string; rateLimit?: number }): Promise<{ key: string; apiKey: ApiKey }>
revokeApiKey(id: string): Promise<void>
```

### Metrics

```typescript
getMetrics(): Promise<Metric[]>
getMetric(id: string): Promise<Metric>
createMetric(input: MetricInput): Promise<Metric>
updateMetric(id: string, input: Partial<MetricInput>): Promise<Metric>
certifyMetric(id: string): Promise<Metric>
queryMetric(id: string, input: { dimensions?: string[]; filters?: Record<string, any>; granularity?: string }): Promise<any>
getMetricCache(id: string): Promise<{ value: number; sampleSize: number | null } | null>
```

### Dashboards

```typescript
getDashboards(): Promise<Dashboard[]>
getDashboard(id: string): Promise<Dashboard>
getDashboardBySlug(slug: string): Promise<Dashboard>
createDashboard(input: DashboardInput): Promise<Dashboard>
updateDashboard(id: string, input: Partial<DashboardInput>): Promise<Dashboard>
deleteDashboard(id: string): Promise<void>
```

### Alerts

```typescript
getAlertRules(): Promise<AlertRule[]>
createAlertRule(input: AlertRuleInput): Promise<AlertRule>
updateAlertRule(id: string, input: Partial<AlertRuleInput>): Promise<AlertRule>
getAlertIncidents(): Promise<AlertIncident[]>
acknowledgeAlertIncident(id: string): Promise<void>
resolveAlertIncident(id: string): Promise<void>
```

### AI Agents

```typescript
runAgent(input: {
  agentType: string;
  input: Record<string, unknown>;
  orgId: string;
  userId: string;
  sessionId?: string;
  options?: { timeoutMs?: number; maxRetries?: number };
}): Promise<{ runId: string; output: unknown }>

getAgentRuns(filters?: { agentType?: string; status?: string }): Promise<AgentRun[]>
getAgentRun(runId: string): Promise<AgentRun>
cancelAgentRun(runId: string): Promise<void>
```

### Billing

```typescript
createCheckoutSession(input: { plan: 'pro' | 'team' | 'enterprise'; successUrl: string; cancelUrl: string }): Promise<{ sessionId: string; url: string }>
createPortalSession(returnUrl: string): Promise<{ url: string }>
getUsage(): Promise<Record<string, number>>
```

## Agent Packages (`@pix/agents`)

```typescript
import { AgentOrchestrator } from '@pix/agents';

const orchestrator = new AgentOrchestrator({
  openaiApiKey: string;
  supabaseUrl: string;
  supabaseServiceKey: string;
});

const result = await orchestrator.execute({
  type: 'sql' | 'forecast' | 'insight' | 'root-cause' | 'narrative' | 'data-quality' | 'pre-mortem' | 'action';
  query: string;
  orgId: string;
  userId: string;
  context?: Record<string, unknown>;
});
```

## Service Packages (`@pix/services`)

```typescript
import { SQLValidator } from "@pix/services";

const validator = new SQLValidator();
const result = await validator.validate("SELECT * FROM users");
// { valid: boolean; errors?: string[]; warnings?: string[] }
```
