import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";
import Papa from "papaparse";
import { renderChartSvg, renderDashboardPng } from "../dist/viz/echarts.js";
import { svgToPng } from "../dist/viz/png.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const root = join(__dirname, "..");
const outDir = join(root, "hy3-data-output", "demo-frames");
mkdirSync(outDir, { recursive: true });

function loadCsv(filePath) {
  const text = readFileSync(filePath, "utf-8");
  const parsed = Papa.parse(text, { header: true, skipEmptyLines: true, dynamicTyping: true });
  return { columns: parsed.meta.fields, rows: parsed.data };
}

function groupBy(rows, keyFn, valueFn, reducer = (acc, v) => acc + v, init = 0) {
  const map = new Map();
  for (const row of rows) {
    const k = keyFn(row);
    const v = valueFn(row);
    if (k == null || v == null) continue;
    map.set(k, reducer(map.has(k) ? map.get(k) : init, v));
  }
  return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
}

function aggregateSum(rows, keyCol, valueCol) {
  return groupBy(rows, (r) => r[keyCol], (r) => Number(r[valueCol]) || 0);
}

let frameIndex = 0;
function nextFramePath() {
  const name = `frame-${String(frameIndex).padStart(3, "0")}`;
  frameIndex++;
  return join(outDir, `${name}.png`);
}

async function saveChartPng(chartType, table, config, width = 800, height = 600) {
  const svg = renderChartSvg(chartType, table, { ...config, width, height, theme: "dark" });
  const png = await svgToPng(svg, width, height);
  const path = nextFramePath();
  writeFileSync(path, png);
  console.log("generated", path);
  return path;
}

async function main() {
  const customers = loadCsv(join(root, "sample_data", "complex", "customers.csv"));
  const clinical = loadCsv(join(root, "sample_data", "complex", "clinical_trial.csv"));
  const geo = loadCsv(join(root, "sample_data", "complex", "hierarchical_geo_sales.csv"));
  const ecommerce = loadCsv(join(root, "sample_data", "complex", "ecommerce_sales.csv"));
  const marketing = loadCsv(join(root, "sample_data", "complex", "marketing_campaigns.csv"));

  // 1. Bubble chart: age vs lifetime_value sized by purchase_count
  await saveChartPng("bubble", customers, {
    x_column: "age",
    y_column: "lifetime_value",
    size_column: "purchase_count",
    title: "年龄与生命周期价值气泡图",
  });

  // 2. Boxplot: treatment_group vs response_score
  await saveChartPng("boxplot", clinical, {
    x_column: "treatment_group",
    y_column: "response_score",
    title: "不同治疗组响应分数箱线图",
  });

  // 3. Sunburst: hierarchical revenue by region → city → category
  const sunburstData = groupBy(
    geo.rows,
    (r) => `${r.region} / ${r.city} / ${r.category}`,
    (r) => Number(r.revenue) || 0
  );
  const sunburstTable = {
    columns: ["path", "revenue"],
    rows: sunburstData.map((d) => ({ path: d.name, revenue: d.value })),
  };
  await saveChartPng("sunburst", sunburstTable, {
    x_column: "path",
    y_column: "revenue",
    title: "旭日图展示各区域各城市各品类营收情况",
  });

  // 4. Dashboard: aggregate several views
  const dailyRevenue = aggregateSum(ecommerce.rows, "date", "revenue")
    .sort((a, b) => String(a.name).localeCompare(String(b.name)))
    .map((d) => ({ date: d.name, revenue: d.value }));
  const categoryRegionRevenue = groupBy(
    ecommerce.rows,
    (r) => `${r.category}|${r.region}`,
    (r) => Number(r.revenue) || 0
  ).map((d) => {
    const [category, region] = d.name.split("|");
    return { category, region, revenue: d.value };
  });
  const campaignConversions = aggregateSum(marketing.rows, "campaign_id", "conversions")
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((d) => ({ campaign_id: d.name, conversions: d.value }));

  const dashPng = await renderDashboardPng(
    [
      {
        chartType: "area",
        table: { columns: ["date", "revenue"], rows: dailyRevenue },
        config: { x_column: "date", y_column: "revenue", title: "每日营收趋势" },
      },
      {
        chartType: "stacked_bar",
        table: { columns: ["category", "region", "revenue"], rows: categoryRegionRevenue },
        config: {
          x_column: "category",
          y_column: "revenue",
          group_column: "region",
          title: "各品类分区域营收",
        },
      },
      {
        chartType: "scatter",
        table: marketing,
        config: { x_column: "spend", y_column: "revenue", title: "营销花费与营收关系" },
      },
      {
        chartType: "funnel",
        table: { columns: ["campaign_id", "conversions"], rows: campaignConversions },
        config: { x_column: "campaign_id", y_column: "conversions", title: "营销转化漏斗" },
      },
    ],
    "电商与营销活动综合数据大屏",
    "premium"
  );
  const dashPath = nextFramePath();
  writeFileSync(dashPath, dashPng);
  console.log("generated", dashPath);

  // Normalize all frames to a fixed 800x600 canvas with white padding
  const normalizeResult = spawnSync(
    "ffmpeg",
    [
      "-framerate", "0.5",
      "-i", join(outDir, "frame-%03d.png"),
      "-vf",
      "scale=800:600:force_original_aspect_ratio=decrease:flags=lanczos,pad=800:600:(ow-iw)/2:(oh-ih)/2:#0B1120,format=rgb24",
      "-y",
      join(outDir, "norm-%03d.png"),
    ],
    { stdio: "inherit" }
  );
  if (normalizeResult.status !== 0) {
    console.error("ffmpeg normalize failed", normalizeResult.status);
    process.exit(1);
  }

  // Build GIF with ffmpeg: each frame shown for 2s (0.5 fps)
  const gifPath = join(root, "assets", "demo.gif");
  const result = spawnSync(
    "ffmpeg",
    [
      "-framerate", "0.5",
      "-i", join(outDir, "norm-%03d.png"),
      "-vf",
      "split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
      "-loop", "0",
      "-y",
      gifPath,
    ],
    { stdio: "inherit" }
  );

  if (result.status !== 0) {
    console.error("ffmpeg failed", result.status);
    process.exit(1);
  }
  console.log("demo.gif saved to", gifPath);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
