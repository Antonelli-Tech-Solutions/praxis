import { createApiDataProvider } from "./apiClient";
import type { DataSourceConfig } from "../config/dataSource";
import { createMockDataProvider } from "./mockProvider";
import type { DataProvider } from "./dataProvider";

export function resolveDataProvider(config: DataSourceConfig): DataProvider {
  if (config.mode === "mock") {
    return createMockDataProvider(config.evalMetricsUrl, config.apiToken);
  }

  if (!config.apiBaseUrl) {
    return createMockDataProvider(config.evalMetricsUrl, config.apiToken);
  }

  return createApiDataProvider(
    config.apiBaseUrl,
    config.apiToken,
    config.evalMetricsUrl,
  );
}

/** @deprecated Use resolveDataProvider with DataSourceConfig */
export function getDataProvider(): DataProvider {
  const baseUrl = import.meta.env.VITE_PRAXIS_API_BASE_URL?.trim();
  if (baseUrl) {
    const token = import.meta.env.VITE_PRAXIS_API_TOKEN?.trim();
    return createApiDataProvider(baseUrl, token || undefined);
  }
  return createMockDataProvider();
}
