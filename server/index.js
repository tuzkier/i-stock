import express from "express";
import { createServer as createViteServer } from "vite";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createMarketDataSource } from "../src/domain/market-data-source.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const app = express();
const port = Number(process.env.PORT || 5173);
const isProduction = process.env.NODE_ENV === "production";
const marketDataSource = createMarketDataSource();

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
