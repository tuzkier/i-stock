import express from "express";
import { createServer as createViteServer } from "vite";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { createMarketDataSource } from "../src/domain/market-data-source.ts";
import { buildHoldingsPanel } from "../src/domain/holdings-panel.ts";
import { resolveTradeStrategy } from "../src/domain/trade-signals.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const app = express();
const port = Number(process.env.PORT || 4271);
const isProduction = process.env.NODE_ENV === "production";
const marketDataSource = createMarketDataSource();
const execFileAsync = promisify(execFile);

const FUTUD_HOST = process.env.FUTUD_HOST ?? "127.0.0.1";
const FUTUD_PORT = String(process.env.FUTUD_PORT ?? "11111");
const PYTHON_BIN = process.env.FUTUD_PYTHON_BIN ?? "python3";

async function queryPositions({ market = "HK", env = "REAL" } = {}) {
  const { stdout } = await execFileAsync(
    PYTHON_BIN,
    [path.join(root, "server", "futud-positions.py"), "--market", market, "--env", env, "--host", FUTUD_HOST, "--port", FUTUD_PORT],
    { timeout: 60000 }
  );
  const payload = JSON.parse(stdout);
  if (payload.error) throw new Error(`${payload.error}: ${payload.detail ?? ""}`);
  return payload.positions ?? [];
}

app.get("/api/chart/:symbol", async (request, response) => {
  const symbol = String(request.params.symbol ?? "");
  const range = String(request.query.range ?? "6mo");
  const forceRefresh = request.query.forceRefresh === "1" || request.query.forceRefresh === "true";

  if (!symbol.trim()) {
    response.status(400).json({ error: "Missing symbol" });
    return;
  }

  const envelope = await marketDataSource.fetchSeries(symbol, range, {
    forceRefresh
  });

  response.json(envelope);
});

// 真实持仓操作面板：查 FutuOpenD 持仓 + 各标的 K 线 → 组装止损/吊灯/反T 决策（只读，不下单）。
app.get("/api/holdings", async (request, response) => {
  const range = String(request.query.range ?? "1y");
  const env = request.query.env === "SIMULATE" ? "SIMULATE" : "REAL";
  const forceRefresh = request.query.forceRefresh === "1" || request.query.forceRefresh === "true";
  try {
    const positions = await queryPositions({ market: "HK", env });
    const barsBySymbol = {};
    const covered = positions.filter((position) => resolveTradeStrategy(String(position.code ?? "")));
    await Promise.all(
      covered.map(async (position) => {
        const code = String(position.code);
        try {
          const envelope = await marketDataSource.fetchSeries(code, range, { forceRefresh });
          barsBySymbol[code] = envelope.bars ?? [];
        } catch {
          barsBySymbol[code] = [];
        }
      })
    );
    const panel = buildHoldingsPanel(positions, barsBySymbol);
    response.json({ env, range, generatedAt: Date.now(), ...panel });
  } catch (error) {
    response.status(502).json({ error: "holdings_unavailable", detail: String(error?.message ?? error) });
  }
});

if (isProduction) {
  app.use(express.static(path.join(root, "dist")));
  app.get(/.*/, (_, response) => {
    response.sendFile(path.join(root, "dist", "index.html"));
  });
} else {
  const vite = await createViteServer({
    root,
    server: { middlewareMode: true },
    appType: "spa"
  });
  app.use(vite.middlewares);
}

app.listen(port, () => {
  console.log(`MyInvestment running at http://localhost:${port}`);
});
