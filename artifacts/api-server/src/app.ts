import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import { createProxyMiddleware } from "http-proxy-middleware";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());

const FLASK_PORT = process.env["FLASK_PORT"] || "5050";

const FLASK_PREFIXES = [
  "analyze-cry",
  "analyze-photo",
  "diagnose",
  "growth",
  "reminder",
  "emergency",
  "community",
];

for (const prefix of FLASK_PREFIXES) {
  app.use(
    `/api/${prefix}`,
    createProxyMiddleware({
      target: `http://localhost:${FLASK_PORT}`,
      changeOrigin: true,
      pathRewrite: (_path, req) => req.originalUrl,
      on: {
        error: (err: Error, _req: Request, res: Response) => {
          logger.error({ err }, "Flask proxy error");
          if (!res.headersSent) {
            (res as any).status(502).json({ error: "Backend service unavailable" });
          }
        },
      },
    }),
  );
}

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

export default app;
