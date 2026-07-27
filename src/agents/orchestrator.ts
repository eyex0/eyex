import { BaseAgent } from "./base";
import { AnalyticsAgent } from "./analytics-agent";
import { ForecastAgent } from "./forecast-agent";
import { InsightAgent } from "./insight-agent";
import { DataQualityAgent } from "./data-quality-agent";
import { NarrativeAgent } from "./narrative-agent";
import { SQLAgent } from "./sql-agent";
import { RootCauseAgent } from "./root-cause-agent";
import { ActionAgent } from "./action-agent";
import { generateText } from "./llm";
import type { AgentContext, AgentResult } from "./types";

const ROUTER_PROMPT = `You are the πX Agent Orchestrator. Given a user request, classify which agent should handle it.
Respond with ONLY the agent name from this list:
- AnalyticsAgent: data analysis, dashboard generation, chart creation
- ForecastAgent: predictions, forecasting, projections, trends
- InsightAgent: business insights, findings, observations
- DataQualityAgent: data validation, quality checks, cleaning
- NarrativeAgent: executive summaries, reports, business narratives
- SQLAgent: SQL queries, database questions, data retrieval
- RootCauseAgent: anomaly investigation, root cause analysis, failure analysis
- ActionAgent: recommendations, next steps, action items
If the request is general chat or doesn't fit any agent, respond with "General".`;

const ROUTER_SCHEMA = {
  type: "object",
  properties: {
    agent: { type: "string", description: "The agent name to route to" },
    confidence: { type: "number", description: "Routing confidence 0-100" },
    reason: { type: "string", description: "Why this agent was chosen" },
  },
  required: ["agent", "confidence", "reason"],
};

export interface OrchestratorStep {
  agent: string;
  input: string;
  result: AgentResult;
  duration: number;
}

export interface OrchestrationResult {
  final: string;
  steps: OrchestratorStep[];
  structured?: Record<string, unknown>;
}

export class OrchestratorAgent extends BaseAgent {
  private agents: Map<string, BaseAgent> = new Map();

  constructor() {
    super({
      name: "Orchestrator",
      description: "Routes requests to the right agent and manages multi-step workflows",
      systemPrompt: ROUTER_PROMPT,
    });

    this.register(new AnalyticsAgent());
    this.register(new ForecastAgent());
    this.register(new InsightAgent());
    this.register(new DataQualityAgent());
    this.register(new NarrativeAgent());
    this.register(new SQLAgent());
    this.register(new RootCauseAgent());
    this.register(new ActionAgent());
  }

  private register(agent: BaseAgent): void {
    this.agents.set(agent.config.name, agent);
  }

  async execute(context: AgentContext): Promise<AgentResult> {
    try {
      const result = await this.orchestrate(context);
      return this.success(result.final, result.structured);
    } catch (err) {
      return this.error(
        `Orchestration failed: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }

  async orchestrate(context: AgentContext): Promise<OrchestrationResult> {
    const lastMessage = context.messages[context.messages.length - 1]?.text || "";
    const steps: OrchestratorStep[] = [];

    const routeResult = await generateText(
      `User request: "${lastMessage}"
Context: ${JSON.stringify(context.data || {})}
Which agent should handle this?`,
      {
        systemInstruction: ROUTER_PROMPT,
        responseSchema: ROUTER_SCHEMA,
        temperature: 0.1,
      },
    );

    let routing: { agent: string; confidence: number; reason: string };
    try {
      routing = JSON.parse(routeResult);
    } catch {
      routing = { agent: "General", confidence: 0, reason: "Fallback — unparseable routing" };
    }

    const targetAgent = this.agents.get(routing.agent);

    if (targetAgent && routing.confidence >= 40) {
      const start = Date.now();
      const agentContext: AgentContext = {
        messages: context.messages,
        data: context.data,
        userId: context.userId,
      };
      const agentResult = await targetAgent.execute(agentContext);
      const duration = Date.now() - start;

      steps.push({
        agent: targetAgent.config.name,
        input: lastMessage,
        result: agentResult,
        duration,
      });

      if (agentResult.structured) {
        return {
          final: agentResult.output,
          steps,
          structured: agentResult.structured,
        };
      }

      return { final: agentResult.output, steps };
    }

    const generalResponse = await generateText(
      `User says: "${lastMessage}"
${context.data ? `Context: ${JSON.stringify(context.data)}` : ""}
Respond helpfully as the πX AI Copilot. Be concise and professional.`,
      { temperature: 0.5 },
    );

    return {
      final: generalResponse,
      steps: [
        {
          agent: "General",
          input: lastMessage,
          result: { success: true, output: generalResponse, agentName: "General" },
          duration: 0,
        },
      ],
    };
  }
}
