/**
 * DynamicWidgetRenderer — Maps widget type to React component.
 * No hardcoded dashboards — widgets are instantiated from JSON.
 */
import React, { lazy, Suspense } from 'react';

const KPIComponent = lazy(() => import('./KPIComponent').then(m => ({ default: m.KPIComponent })));
const ChartComponent = lazy(() => import('./ChartComponent').then(m => ({ default: m.ChartComponent })));
const DecisionComponent = lazy(() => import('./DecisionComponent').then(m => ({ default: m.DecisionComponent })));

interface WidgetDef {
  id: string;
  type: string;
  label: string;
  config: Record<string, any>;
  component: string;
  data_keys: string[];
}

interface Props {
  widget: WidgetDef;
  orgId: string;
  events?: any[];
}

export const DynamicWidgetRenderer: React.FC<Props> = ({ widget, orgId, events = [] }) => {
  const { component } = widget;

  // Map component name to lazy-loaded React component
  const componentMap: Record<string, React.LazyExoticComponent<React.FC<any>>> = {
    KPIComponent,
    ChartComponent,
    DecisionComponent,
  };

  const Component = componentMap[component];

  if (!Component) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Widget: {widget.label} (component: {component})
      </div>
    );
  }

  return (
    <Suspense fallback={<div className="animate-pulse h-32 bg-muted rounded" />}>
      <Component
        widget={widget}
        orgId={orgId}
        events={events}
      />
    </Suspense>
  );
};
