from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent
from packages.cognitive_kernel.agent_runtime.tools import get_registry


class ConfigFile(BaseModel):
    path: str = Field(description="Relative configuration file path (e.g. docker-compose.yml)")
    content: str = Field(description="Complete configuration file content")
    type: str = Field(description="Configuration type: 'docker', 'ci', 'deployment', 'monitoring', 'infrastructure'")


class DevOpsOutput(BaseModel):
    config_files: list[ConfigFile] = Field(description="Configuration files to create with full content")
    deployment_steps: list[str] = Field(description="Step-by-step deployment instructions")
    infrastructure_requirements: list[str] = Field(description="Required infrastructure: services, resources, permissions")
    cicd_pipeline: str = Field(description="Description of the CI/CD pipeline stages and tools")
    monitoring_setup: list[str] = Field(description="Monitoring, logging, and alerting configuration")
    security_notes: list[str] = Field(description="Security considerations: network, secrets, access control")
    estimated_resources: str = Field(description="Estimated infrastructure resources (CPU, RAM, storage, cost)")


SYSTEM_PROMPT = """You are the **DevOps Agent** for πX Technologies QORX.

Your role is to handle all infrastructure, deployment, CI/CD, and operations configurations.

**Responsibilities:**
1. **Docker**: Dockerfile, docker-compose, multi-stage builds, optimization
2. **CI/CD**: GitHub Actions, GitLab CI, or similar pipeline configurations
3. **Deployment**: Cloud deployment (Cloudflare Workers, AWS, GCP, Azure), serverless, containers
4. **Monitoring**: Logging, metrics, health checks, alerting
5. **Security**: Network policies, secret management, IAM roles, firewall rules
6. **Infrastructure as Code**: Terraform, Pulumi, or CloudFormation templates

**Configuration rules:**
- Use production-ready patterns (health checks, resource limits, restart policies)
- Include security best practices (non-root users, read-only filesystems, secrets)
- Optimize for build speed (layer caching, multi-stage builds)
- Include monitoring and observability from day one
- Document environment variables and their purposes

**Platform-specific knowledge:**
- Cloudflare Workers: wrangler.toml, KV, R2, D1, Queues
- Docker: multi-stage builds, .dockerignore, health checks
- CI/CD: caching, parallel jobs, environment segregation
- Always prefer security by default"""


class DevOpsAgent(NodeAgent):
    @property
    def name(self) -> str:
        return "DevOps"

    @property
    def description(self) -> str:
        return "Handles infrastructure, CI/CD, Docker, deployment, and operations configuration"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def output_schema(self) -> type[BaseModel]:
        return DevOpsOutput

    @property
    def tools(self) -> list[BaseTool]:
        return get_registry().get_tools_for_role("devops")

    def _fallback_output(self, input_text: str, error: str) -> BaseModel:
        return DevOpsOutput(
            config_files=[],
            deployment_steps=["Check LLM availability and retry"],
            infrastructure_requirements=["Standard deployment infrastructure"],
            cicd_pipeline="Could not generate CI/CD configuration due to agent error",
            monitoring_setup=["Set up monitoring manually"],
            security_notes=["Review security requirements manually"],
            estimated_resources="Unknown — agent error occurred",
        )


def create_devops_agent(settings, **kwargs: Any) -> DevOpsAgent:
    return DevOpsAgent(settings=settings, **kwargs)
