import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = join(__dirname, "..", "sample_data", "complex");
mkdirSync(outDir, { recursive: true });

function writeCsv(name, headers, rows) {
  const lines = [headers.join(","), ...rows.map((r) => r.join(","))];
  writeFileSync(join(outDir, name), lines.join("\n") + "\n", "utf-8");
}

// Deterministic-ish pseudo-random based on index
function pseudoRandom(seed) {
  const x = Math.sin(seed * 9999) * 10000;
  return x - Math.floor(x);
}

function randInt(min, max, seed) {
  return Math.floor(pseudoRandom(seed) * (max - min + 1)) + min;
}

function choice(arr, seed) {
  return arr[randInt(0, arr.length - 1, seed)];
}

function round(n, digits = 2) {
  return Number(n.toFixed(digits));
}

function formatDate(year, month, day) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

// 1. ecommerce_sales.csv
{
  const regions = ["North", "South", "East", "West", "Central"];
  const categories = ["Electronics", "Clothing", "Home", "Sports", "Books"];
  const channels = ["Online", "Offline", "Social", "Marketplace"];
  const rows = [];
  let seed = 1;
  for (let i = 0; i < 60; i++) {
    const month = randInt(1, 6, seed++);
    const day = randInt(1, 28, seed++);
    const region = choice(regions, seed++);
    const category = choice(categories, seed++);
    const channel = choice(channels, seed++);
    const units = randInt(20, 500, seed++);
    const discount = round(pseudoRandom(seed++) * 0.3, 2);
    const price = randInt(30, 800, seed++);
    const revenue = round(units * price * (1 - discount), 2);
    const cost = round(revenue * 0.6, 2);
    const profit = round(revenue - cost, 2);
    rows.push([
      formatDate(2024, month, day),
      region,
      category,
      channel,
      units,
      revenue,
      cost,
      profit,
      discount,
    ]);
  }
  writeCsv(
    "ecommerce_sales.csv",
    ["date", "region", "category", "channel", "units_sold", "revenue", "cost", "profit", "discount_rate"],
    rows
  );
}

// 2. customers.csv
{
  const cities = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu", "Hangzhou", "Wuhan"];
  const segments = ["VIP", "Regular", "New"];
  const genders = ["Male", "Female"];
  const rows = [];
  let seed = 100;
  for (let i = 1; i <= 80; i++) {
    const age = randInt(22, 65, seed++);
    const gender = choice(genders, seed++);
    const city = choice(cities, seed++);
    const segment = choice(segments, seed++);
    const purchaseCount = randInt(1, 60, seed++);
    const avgOrderValue = randInt(80, 1200, seed++);
    const lifetimeValue = purchaseCount * avgOrderValue;
    const churnRisk = randInt(0, 100, seed++);
    rows.push([`CUST${String(i).padStart(4, "0")}`, age, gender, city, segment, lifetimeValue, purchaseCount, avgOrderValue, churnRisk]);
  }
  writeCsv(
    "customers.csv",
    ["customer_id", "age", "gender", "city", "segment", "lifetime_value", "purchase_count", "avg_order_value", "churn_risk_score"],
    rows
  );
}

// 3. marketing_campaigns.csv
{
  const channels = ["Search", "Social", "Email", "Display", "Video"];
  const rows = [];
  let seed = 200;
  for (let i = 1; i <= 24; i++) {
    const channel = choice(channels, seed++);
    const budget = randInt(5000, 50000, seed++);
    const spend = round(budget * (0.7 + pseudoRandom(seed++) * 0.3), 2);
    const cpm = randInt(5, 40, seed++);
    const impressions = Math.floor(spend / (cpm / 1000));
    const ctr = round(0.005 + pseudoRandom(seed++) * 0.045, 4);
    const clicks = Math.floor(impressions * ctr);
    const conversionRate = round(0.01 + pseudoRandom(seed++) * 0.09, 4);
    const conversions = Math.floor(clicks * conversionRate);
    const revenue = conversions * randInt(50, 300, seed++);
    rows.push([
      `CMP${String(i).padStart(3, "0")}`,
      channel,
      budget,
      round(spend, 2),
      impressions,
      clicks,
      conversions,
      revenue,
    ]);
  }
  writeCsv(
    "marketing_campaigns.csv",
    ["campaign_id", "channel", "budget", "spend", "impressions", "clicks", "conversions", "revenue"],
    rows
  );
}

// 4. clinical_trial.csv
{
  const groups = ["Placebo", "Drug_A", "Drug_B"];
  const rows = [];
  let seed = 300;
  for (let i = 1; i <= 90; i++) {
    const group = choice(groups, seed++);
    const age = randInt(25, 75, seed++);
    const baseline = randInt(60, 90, seed++);
    const effect = group === "Placebo" ? randInt(-3, 5, seed++) : group === "Drug_A" ? randInt(5, 20, seed++) : randInt(10, 30, seed++);
    const response = baseline + effect;
    const adverse = randInt(0, group === "Placebo" ? 2 : 5, seed++);
    rows.push([`P${String(i).padStart(3, "0")}`, group, age, baseline, response, adverse]);
  }
  writeCsv(
    "clinical_trial.csv",
    ["patient_id", "treatment_group", "age", "baseline_score", "response_score", "adverse_event_count"],
    rows
  );
}

// 5. employee_performance.csv
{
  const departments = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"];
  const levels = ["Junior", "Senior", "Lead", "Manager"];
  const rows = [];
  let seed = 400;
  for (let i = 1; i <= 60; i++) {
    const dept = choice(departments, seed++);
    const level = choice(levels, seed++);
    const tenure = randInt(1, 15, seed++);
    const performance = randInt(60, 100, seed++);
    const baseSalary = { Junior: 50000, Senior: 80000, Lead: 110000, Manager: 150000 }[level];
    const salary = baseSalary + randInt(-5000, 20000, seed++);
    const projects = randInt(1, 12, seed++);
    const satisfaction = randInt(50, 100, seed++);
    rows.push([`EMP${String(i).padStart(3, "0")}`, dept, level, tenure, performance, salary, projects, satisfaction]);
  }
  writeCsv(
    "employee_performance.csv",
    ["employee_id", "department", "level", "tenure_years", "performance_score", "salary", "projects_completed", "satisfaction_score"],
    rows
  );
}

// 6. reviews.csv (more realistic Chinese comments)
{
  const comments = [
    "产品质量非常好，物流也很快，下次还会购买。",
    "包装有点破损，但是产品本身没问题，希望改进包装。",
    "性价比很高，推荐给大家。",
    "客服态度一般，解决问题不够及时。",
    "用了两周，效果超出预期，五星好评。",
    "颜色和描述有差异，但整体还可以。",
    "发货太慢了，等了一周才收到。",
    "功能齐全，操作简单，老人也能用。",
    "价格有点贵，但是质量对得起价格。",
    "不太满意，用了几天就出现小问题。",
    "设计很漂亮，放在家里很上档次。",
    "续航时间比想象中短，其他都还好。",
    "非常满意的一次购物体验。",
    "说明书不够详细，研究了好久才会用。",
    "会推荐给朋友，值得信赖的品牌。",
    "噪音有点大，影响使用体验。",
    "材质很好，摸起来很舒服。",
    "尺寸不合适，退货流程太麻烦了。",
    "物流神速，昨天下单今天就到了。",
    "整体不错，符合我的预期。",
  ];
  const rows = comments.map((c, i) => [i + 1, c, randInt(1, 5, 500 + i)]);
  writeCsv("reviews.csv", ["review_id", "comment", "rating"], rows);
}

// 7. hierarchical_geo_sales.csv for sunburst/treemap
{
  const data = [
    ["North", "Beijing", "Electronics", 450000],
    ["North", "Beijing", "Clothing", 230000],
    ["North", "Tianjin", "Electronics", 180000],
    ["North", "Tianjin", "Home", 120000],
    ["South", "Guangzhou", "Electronics", 520000],
    ["South", "Guangzhou", "Sports", 150000],
    ["South", "Shenzhen", "Electronics", 680000],
    ["South", "Shenzhen", "Clothing", 210000],
    ["East", "Shanghai", "Electronics", 610000],
    ["East", "Shanghai", "Home", 340000],
    ["East", "Hangzhou", "Clothing", 190000],
    ["West", "Chengdu", "Sports", 170000],
    ["West", "Chengdu", "Food", 140000],
    ["Central", "Wuhan", "Electronics", 290000],
    ["Central", "Wuhan", "Home", 160000],
  ];
  writeCsv("hierarchical_geo_sales.csv", ["region", "city", "category", "revenue"], data);
}

console.log("Complex sample datasets generated in sample_data/complex/");
