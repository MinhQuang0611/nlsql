import styled from 'styled-components';
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Select, Row, Col, Table, Typography } from 'antd';

const { Text } = Typography;

// Declare window.vegaEmbed (loaded via CDN in _app.tsx)
declare global {
  interface Window {
    vegaEmbed: any;
  }
}

// ─── Chart type options ─────────────────────────────────────────────
const CHART_TYPE_OPTIONS = [
  { label: '📊 Bar', value: 'bar' },
  { label: '📈 Line', value: 'line' },
  { label: '🔵 Pie', value: 'pie' },
  { label: '📉 Area', value: 'area' },
  { label: '⬡ Scatter', value: 'scatter' },
  { label: '🔢 Number', value: 'number' },
  { label: '📋 Table', value: 'table' },
];

// ─── Vega mark mapping ──────────────────────────────────────────────
const MARK_MAP: Record<string, string> = {
  bar: 'bar',
  line: 'line',
  area: 'area',
  pie: 'arc',
  scatter: 'point',
};

// ─── Styled ─────────────────────────────────────────────────────────
const ChartPanel = styled.div`
  border: 1px solid var(--gray-4, #d9d9d9);
  border-radius: 12px;
  overflow: hidden;
  margin-top: 16px;
  background: var(--white, #fff);
`;

const Toolbar = styled.div`
  background: var(--gray-2, #fafafa);
  padding: 12px 16px;
  border-bottom: 1px solid var(--gray-4, #d9d9d9);

  .ant-select { min-width: 120px; }
  label {
    display: block;
    font-size: 11px;
    color: var(--gray-7, #8c8c8c);
    margin-bottom: 4px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
`;

const ChartArea = styled.div`
  padding: 16px;
  min-height: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const NumberDisplay = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 280px;
  gap: 8px;
`;

const NumberValue = styled.div`
  font-size: 56px;
  font-weight: 700;
  color: var(--blue-6, #1677ff);
  line-height: 1;
`;

const NumberLabel = styled.div`
  font-size: 14px;
  color: var(--gray-7, #8c8c8c);
  font-weight: 500;
`;

// ─── Build a Vega-Lite JSON spec ────────────────────────────────────
function buildVegaLiteSpec(
  chartType: string,
  xAxis: string,
  yAxis: string,
  color: string | null,
  title: string | null,
  xLabel: string | null,
  yLabel: string | null,
  data: Record<string, any>[],
) {
  const mark = MARK_MAP[chartType] || 'bar';
  const xField = xAxis || 'x';
  const yField = yAxis || 'y';

  const encoding: any = {};

  if (mark === 'arc') {
    encoding.theta = { field: yField, type: 'quantitative', stack: true };
    encoding.color = { field: xField, type: 'nominal', title: xLabel || xField };
  } else {
    encoding.x = {
      field: xField,
      type: 'nominal',
      title: xLabel || xField,
      axis: { labelAngle: -45 },
    };
    encoding.y = {
      field: yField,
      type: 'quantitative',
      title: yLabel || yField,
    };
    if (color) {
      encoding.color = { field: color, type: 'nominal' };
    }
  }

  return {
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    title: title || undefined,
    width: 'container',
    height: 300,
    autosize: { type: 'fit', contains: 'padding' },
    data: { values: data },
    mark: {
      type: mark,
      tooltip: true,
      ...(mark === 'line' ? { point: true } : {}),
      ...(mark === 'arc' ? { innerRadius: 50 } : {}),
    },
    encoding,
    config: {
      view: { stroke: 'transparent' },
      font: 'Inter, sans-serif',
    },
  };
}

// ─── Props ──────────────────────────────────────────────────────────
interface Props {
  chartConfig: {
    chart_type?: string;
    x_axis?: string | null;
    y_axis?: string | null;
    group_by?: string | null;
    title?: string | null;
    x_label?: string | null;
    y_label?: string | null;
  };
  data: Record<string, any>[];
}

// ─── Component ──────────────────────────────────────────────────────
export default function ChatChartAnswer({ chartConfig, data }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);

  // All column names available in data
  const columns = useMemo(() => {
    if (!data || data.length === 0) return [];
    return Object.keys(data[0]);
  }, [data]);

  const columnOptions = useMemo(
    () => columns.map((c) => ({ label: c, value: c })),
    [columns],
  );

  // Controlled state for each selector (instant updates, no form batching)
  const [chartType, setChartType] = useState(() => {
    return (chartConfig?.chart_type || 'bar').toLowerCase();
  });
  const [xAxis, setXAxis] = useState(() => {
    return chartConfig?.x_axis || columns[0] || null;
  });
  const [yAxis, setYAxis] = useState(() => {
    return chartConfig?.y_axis || columns[1] || columns[0] || null;
  });
  const [color, setColor] = useState<string | null>(() => {
    return chartConfig?.group_by || null;
  });

  // Sync state when chartConfig/columns change (new message)
  useEffect(() => {
    const ct = (chartConfig?.chart_type || 'bar').toLowerCase();
    setChartType(ct);
    setXAxis(chartConfig?.x_axis || columns[0] || null);
    setYAxis(chartConfig?.y_axis || columns[1] || columns[0] || null);
    setColor(chartConfig?.group_by || null);
  }, [chartConfig, columns]);

  // Render the vega chart whenever state changes
  const renderChart = useCallback(() => {
    if (!chartRef.current) return;
    if (chartType === 'table' || chartType === 'number') return;
    if (!window.vegaEmbed) {
      console.warn('vegaEmbed not loaded yet');
      return;
    }

    const spec = buildVegaLiteSpec(
      chartType, xAxis, yAxis, color,
      chartConfig?.title || null,
      chartConfig?.x_label || null,
      chartConfig?.y_label || null,
      data,
    );

    window.vegaEmbed(chartRef.current, spec, {
      actions: false,
      renderer: 'svg',
    }).catch((err: any) => console.error('vegaEmbed error:', err));
  }, [chartType, xAxis, yAxis, color, data, chartConfig]);

  useEffect(() => {
    renderChart();
  }, [renderChart]);

  if (!data || data.length === 0) return null;

  const isChart = chartType !== 'table' && chartType !== 'number';

  return (
    <ChartPanel>
      <Toolbar>
        <Row gutter={12}>
          <Col span={6}>
            <label>Chart Type</label>
            <Select
              size="small"
              value={chartType}
              onChange={(v) => setChartType(v)}
              options={CHART_TYPE_OPTIONS}
              style={{ width: '100%' }}
            />
          </Col>
          {isChart && (
            <>
              <Col span={6}>
                <label>X-Axis (Column)</label>
                <Select
                  size="small"
                  value={xAxis}
                  onChange={(v) => setXAxis(v)}
                  options={columnOptions}
                  allowClear
                  placeholder="Select column"
                  style={{ width: '100%' }}
                />
              </Col>
              <Col span={6}>
                <label>Y-Axis (Value)</label>
                <Select
                  size="small"
                  value={yAxis}
                  onChange={(v) => setYAxis(v)}
                  options={columnOptions}
                  allowClear
                  placeholder="Select value"
                  style={{ width: '100%' }}
                />
              </Col>
              <Col span={6}>
                <label>Color / Group</label>
                <Select
                  size="small"
                  value={color}
                  onChange={(v) => setColor(v || null)}
                  options={columnOptions}
                  allowClear
                  placeholder="None"
                  style={{ width: '100%' }}
                />
              </Col>
            </>
          )}
        </Row>
      </Toolbar>

      <ChartArea>
        {chartType === 'table' ? (
          <div style={{ width: '100%' }}>
            <Table
              dataSource={data}
              columns={columns.map((k) => ({
                title: k,
                dataIndex: k,
                key: k,
                ellipsis: true,
              }))}
              pagination={{ pageSize: 10, size: 'small', showTotal: (t: number) => `${t} rows` }}
              size="small"
              bordered
              scroll={{ x: 'max-content' }}
            />
          </div>
        ) : chartType === 'number' ? (
          <NumberDisplay>
            <NumberLabel>
              {chartConfig?.title || yAxis || columns[0]}
            </NumberLabel>
            <NumberValue>
              {(() => {
                const field = yAxis || columns[0];
                const val = data[0]?.[field];
                return typeof val === 'number'
                  ? val.toLocaleString()
                  : String(val ?? '-');
              })()}
            </NumberValue>
          </NumberDisplay>
        ) : (
          <div ref={chartRef} style={{ width: '100%', minHeight: 320 }} />
        )}
      </ChartArea>
    </ChartPanel>
  );
}
