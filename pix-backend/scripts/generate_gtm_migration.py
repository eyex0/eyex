from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models import gtm


models = [
    gtm.Lead, gtm.PipelineDeal, gtm.DealActivity, gtm.EnterpriseDemo,
    gtm.CustomerOnboarding, gtm.OnboardingTask, gtm.CustomerHealth,
    gtm.UsageMetric, gtm.CustomerFeedback, gtm.RetentionWorkflow,
    gtm.EnterprisePricing, gtm.UsageBasedBilling, gtm.MarketplaceRevenue,
    gtm.IndustrySolution, gtm.Partner, gtm.PartnershipIntegration,
    gtm.MarketOpportunity, gtm.SalesPrediction, gtm.CaseStudy,
    gtm.ROICalculator, gtm.CustomerSuccessReport, gtm.BusinessImpactMeasurement,
]

lines: list[str] = []
lines.append('"""Add GTM and Growth System tables."""')
lines.append("from __future__ import annotations")
lines.append("")
lines.append("from collections.abc import Sequence")
lines.append("")
lines.append("import sqlalchemy as sa")
lines.append("from alembic import op")
lines.append("from sqlalchemy.dialects import postgresql")
lines.append("")
lines.append('revision: str = "0004"')
lines.append('down_revision: str | None = "0003"')
lines.append("branch_labels: str | None = None")
lines.append("depends_on: str | None = None")
lines.append("")
lines.append("")
lines.append("def upgrade() -> None:")

for model in models:
    table = model.__table__
    col_lines: list[str] = []
    for col in table.columns:
        col_type = col.type
        if isinstance(col_type, sa.dialects.postgresql.UUID):
            type_str = "sa.UUID()"
        elif isinstance(col_type, sa.dialects.postgresql.JSONB):
            type_str = "postgresql.JSONB()"
        elif isinstance(col_type, sa.Text):
            type_str = "sa.Text()"
        elif isinstance(col_type, sa.String):
            type_str = f"sa.String({col.type.length})"
        elif isinstance(col_type, sa.Integer):
            type_str = "sa.Integer()"
        elif isinstance(col_type, sa.Float):
            type_str = "sa.Float()"
        elif isinstance(col_type, sa.Boolean):
            type_str = "sa.Boolean()"
        elif isinstance(col_type, sa.DateTime):
            type_str = "sa.DateTime(timezone=True)"
        else:
            type_str = repr(col_type)

        nullable = "" if col.nullable else ", nullable=False"
        server_default = ""
        if col.server_default is not None:
            sd = str(col.server_default.arg)
            if "now()" in sd:
                server_default = ', server_default=sa.text("now()")'
            else:
                server_default = f', server_default=sa.text("{sd}")'
        if col.default is not None and col.default.arg is not None:
            arg = col.default.arg
            if isinstance(arg, (list, dict)):
                server_default = ", server_default=sa.text(\"'[]'\")"

        unique = ", unique=True" if col.unique else ""
        col_lines.append(f'        sa.Column("{col.name}", {type_str}{nullable}{server_default}{unique}),')

    fk_lines: list[str] = []
    for fk in table.foreign_keys:
        fk_lines.append(f'        sa.ForeignKeyConstraint(["{fk.parent.name}"], ["{fk.target_fullname}"]),')

    pk_cols = [c.name for c in table.primary_key.columns]
    pk_str = f"        sa.PrimaryKeyConstraint({', '.join(repr(c) for c in pk_cols)}),"

    lines.append("    op.create_table(")
    lines.append(f'        "{table.name}",')
    for cl in col_lines:
        lines.append(cl)
    for fk in fk_lines:
        lines.append(fk)
    lines.append(pk_str)
    lines.append("    )")

    for idx in table.indexes:
        cols = [c.name for c in idx.columns]
        unique = ", unique=True" if idx.unique else ""
        lines.append(f'    op.create_index(op.f("{idx.name}"), "{table.name}", {cols}{unique})')
    lines.append("")

lines.append("    # SubscriptionPlan additions")
lines.append('    op.add_column("subscription_plans", sa.Column("tier", sa.String(50), nullable=True))')
lines.append('    op.add_column("subscription_plans", sa.Column("max_api_calls_per_month", sa.Integer(), nullable=False, server_default=sa.text("10000")))')
lines.append('    op.add_column("subscription_plans", sa.Column("max_storage_gb", sa.Integer(), nullable=False, server_default=sa.text("10")))')
lines.append('    op.add_column("subscription_plans", sa.Column("ai_model_access", postgresql.JSONB(), server_default=sa.text("\'[]\'")))')
lines.append('    op.add_column("subscription_plans", sa.Column("support_level", sa.String(50), server_default=sa.text("\'email\'"), nullable=False))')
lines.append("")
lines.append("")
lines.append("def downgrade() -> None:")
for model in reversed(models):
    lines.append(f'    op.drop_table("{model.__table__.name}")')
lines.append('    op.drop_column("subscription_plans", "support_level")')
lines.append('    op.drop_column("subscription_plans", "ai_model_access")')
lines.append('    op.drop_column("subscription_plans", "max_storage_gb")')
lines.append('    op.drop_column("subscription_plans", "max_api_calls_per_month")')
lines.append('    op.drop_column("subscription_plans", "tier")')

with open("alembic/versions/0004_gtm_growth_system.py", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Migration written to alembic/versions/0004_gtm_growth_system.py")
