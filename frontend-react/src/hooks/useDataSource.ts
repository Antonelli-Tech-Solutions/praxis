import { useCallback, useState } from "react";
import {
  buildConfigFromPreset,
  configDetail,
  persistConfig,
  resolveInitialConfig,
  type DataSourceConfig,
  type DataSourceMode,
} from "../config/dataSource";

export function useDataSource() {
  const [config, setConfig] = useState<DataSourceConfig>(() => resolveInitialConfig());

  const applyConfig = useCallback((presetId: string, customApiBaseUrl?: string) => {
    const next = buildConfigFromPreset(presetId, customApiBaseUrl);
    persistConfig(next);
    setConfig(next);
    return next;
  }, []);

  const mode: DataSourceMode = config.mode;
  const label = config.label;
  const detail = configDetail(config);
  const apiUrl = config.mode === "live" ? config.apiBaseUrl : undefined;

  return {
    config,
    mode,
    label,
    detail,
    apiUrl,
    applyConfig,
  };
}
