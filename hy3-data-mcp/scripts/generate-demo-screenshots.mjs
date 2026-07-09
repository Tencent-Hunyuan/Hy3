import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import Papa from "papaparse";
import { renderChartSvg, renderDashboardPng, renderKnowledgeGraphSvg } from "../dist/viz/echarts.js";
import { renderWordcloudSvg } from "../dist/viz/wordcloud.js";
import { svgToPng } from "../dist/viz/png.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");
const outDir = join(root, "assets", "screenshots");
mkdirSync(outDir, { recursive: true });

function loadCsv(filePath) {
  const text = readFileSync(filePath, "utf-8");
  const parsed = Papa.parse(text, { header: true, skipEmptyLines: true, dynamicTyping: true });
  return { columns: parsed.meta.fields, rows: parsed.data };
}

function groupBy(rows, keyFn, valueFn, reducer = (a, b) => a + b, init = 0) {
  const map = new Map();
  for (const row of rows) {
    const k = keyFn(row);
    const v = valueFn(row);
    if (k == null || v == null) continue;
    map.set(k, reducer(map.has(k) ? map.get(k) : init, v));
  }
  return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
}

async function saveChartPng(name, chartType, table, config, width = 900, height = 550) {
  const svg = renderChartSvg(chartType, table, {
    ...config,
    width,
    height,
    theme: "nature",
  });
  const png = await svgToPng(svg, width, height);
  const path = join(outDir, `${name}.png`);
  writeFileSync(path, png);
  console.log("generated", path);
  return path;
}

async function main() {
  const ecommerce = loadCsv(join(root, "sample_data", "complex", "ecommerce_sales.csv"));
  const customers = loadCsv(join(root, "sample_data", "complex", "customers.csv"));
  const clinical = loadCsv(join(root, "sample_data", "complex", "clinical_trial.csv"));
  const stock = loadCsv(join(root, "sample_data", "stock.csv"));
  const marketing = loadCsv(join(root, "sample_data", "complex", "marketing_campaigns.csv"));
  const geo = loadCsv(join(root, "sample_data", "complex", "hierarchical_geo_sales.csv"));
  const employees = loadCsv(join(root, "sample_data", "complex", "employee_performance.csv"));

  // 1. Stacked bar: category revenue by region
  const stackedRows = groupBy(
    ecommerce.rows,
    (r) => `${r.category}|${r.region}`,
    (r) => Number(r.revenue) || 0
  ).map((d) => {
    const [category, region] = d.name.split("|");
    return { category, region, revenue: d.value };
  });
  await saveChartPng("01-stacked-bar", "stacked_bar", {
    columns: ["category", "region", "revenue"],
    rows: stackedRows,
  }, {
    x_column: "category",
    y_column: "revenue",
    group_column: "region",
    title: "各品类分区域营收",
  });

  // 2. Bubble: age vs lifetime_value
  await saveChartPng("02-bubble", "bubble", customers, {
    x_column: "age",
    y_column: "lifetime_value",
    size_column: "purchase_count",
    title: "客户年龄与生命周期价值",
  });

  // 3. Boxplot: treatment vs response
  await saveChartPng("03-boxplot", "boxplot", clinical, {
    x_column: "treatment_group",
    y_column: "response_score",
    title: "不同治疗组响应分数箱线图",
  });

  // 4. Candlestick
  await saveChartPng("04-candlestick", "candlestick", stock, {
    x_column: "date",
    open_column: "open",
    close_column: "close",
    high_column: "high",
    low_column: "low",
    title: "股票价格 K 线图",
  });

  // 5. Funnel
  const funnelRows = groupBy(marketing.rows, (r) => r.campaign_id, (r) => Number(r.conversions) || 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((d) => ({ campaign_id: d.name, conversions: d.value }));
  await saveChartPng("05-funnel", "funnel", { columns: ["campaign_id", "conversions"], rows: funnelRows }, {
    x_column: "campaign_id",
    y_column: "conversions",
    title: "营销转化漏斗",
  });

  // 6. Sunburst
  const sunburstRows = groupBy(
    geo.rows,
    (r) => `${r.region} / ${r.city} / ${r.category}`,
    (r) => Number(r.revenue) || 0
  ).map((d) => ({ path: d.name, revenue: d.value }));
  await saveChartPng("06-sunburst", "sunburst", { columns: ["path", "revenue"], rows: sunburstRows }, {
    x_column: "path",
    y_column: "revenue",
    title: "区域城市品类营收旭日图",
  });

  // 7. Radar: avg performance by department
  const radarRows = groupBy(
    employees.rows,
    (r) => r.department,
    (r) => Number(r.performance_score) || 0,
    (a, b) => a + b,
    0
  ).map((d) => {
    const count = employees.rows.filter((r) => r.department === d.name).length || 1;
    return { department: d.name, score: Math.round(d.value / count) };
  });
  await saveChartPng("07-radar", "radar", { columns: ["department", "score"], rows: radarRows }, {
    x_column: "department",
    y_column: "score",
    title: "各部门平均绩效雷达图",
  });

  // 8. Wordcloud
  const wordcloudSvg = renderWordcloudSvg(
    [
      { word: "人工智能", weight: 100 },
      { word: "数据可视化", weight: 90 },
      { word: "大模型", weight: 85 },
      { word: "Hy3", weight: 80 },
      { word: "图表", weight: 70 },
      { word: "分析", weight: 65 },
      { word: "MCP", weight: 60 },
      { word: "自然语言", weight: 55 },
      { word: "洞察", weight: 50 },
      { word: "报告", weight: 45 },
      { word: "交互", weight: 40 },
      { word: "主题", weight: 35 },
    ],
    "关键词词云",
    900,
    550,
    "nature"
  );
  const wordcloudPng = await svgToPng(wordcloudSvg, 900, 550);
  writeFileSync(join(outDir, "08-wordcloud.png"), wordcloudPng);
  console.log("generated", join(outDir, "08-wordcloud.png"));

  // 9. Knowledge graph
  const kgSvg = renderKnowledgeGraphSvg(
    [
      { id: "Hy3", group: 1 },
      { id: "MCP", group: 1 },
      { id: "数据可视化", group: 2 },
      { id: "词云", group: 2 },
      { id: "知识图谱", group: 2 },
      { id: "ECharts", group: 3 },
      { id: "CSV", group: 3 },
      { id: "PDF", group: 3 },
    ],
    [
      { source: "Hy3", target: "MCP", relation: "powers" },
      { source: "MCP", target: "数据可视化", relation: "generates" },
      { source: "MCP", target: "词云", relation: "generates" },
      { source: "MCP", target: "知识图谱", relation: "generates" },
      { source: "数据可视化", target: "ECharts", relation: "renders with" },
      { source: "词云", target: "ECharts", relation: "renders with" },
      { source: "知识图谱", target: "ECharts", relation: "renders with" },
      { source: "数据可视化", target: "CSV", relation: "reads" },
      { source: "数据可视化", target: "PDF", relation: "reads" },
    ],
    "知识图谱示例",
    900,
    550,
    "nature"
  );
  const kgPng = await svgToPng(kgSvg, 900, 550);
  writeFileSync(join(outDir, "09-knowledge-graph.png"), kgPng);
  console.log("generated", join(outDir, "09-knowledge-graph.png"));

  // 10. Dashboard
  const dailyRevenue = groupBy(ecommerce.rows, (r) => r.date, (r) => Number(r.revenue) || 0)
    .sort((a, b) => String(a.name).localeCompare(String(b.name)))
    .map((d) => ({ date: d.name, revenue: d.value }));
  const categoryRevenue = groupBy(ecommerce.rows, (r) => r.category, (r) => Number(r.revenue) || 0).map(
    (d) => ({ category: d.name, revenue: d.value })
  );
  const spendRevenue = marketing;
  const dashPng = await renderDashboardPng(
    [
      {
        chartType: "area",
        table: { columns: ["date", "revenue"], rows: dailyRevenue },
        config: { x_column: "date", y_column: "revenue", title: "每日营收趋势" },
      },
      {
        chartType: "bar",
        table: { columns: ["category", "revenue"], rows: categoryRevenue },
        config: { x_column: "category", y_column: "revenue", title: "各品类营收" },
      },
      {
        chartType: "scatter",
        table: spendRevenue,
        config: { x_column: "spend", y_column: "revenue", title: "营销花费与营收关系" },
      },
      {
        chartType: "funnel",
        table: { columns: ["campaign_id", "conversions"], rows: funnelRows },
        config: { x_column: "campaign_id", y_column: "conversions", title: "营销转化漏斗" },
      },
    ],
    "电商与营销活动综合数据大屏",
    "nature"
  );
  writeFileSync(join(outDir, "10-dashboard.png"), dashPng);
  console.log("generated", join(outDir, "10-dashboard.png"));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
