import { useEffect, useState } from "react";
import {
  DATA_SOURCE_PRESETS,
  getDeployedApiBaseUrl,
  PRESET_IDS,
} from "../../config/dataSource";
import type { DataSourceConfig } from "../../config/dataSource";

interface DataSourceControlProps {
  config: DataSourceConfig;
  onLoad: (presetId: string, customApiBaseUrl?: string) => void;
}

export function DataSourceControl({ config, onLoad }: DataSourceControlProps) {
  const [presetId, setPresetId] = useState(config.presetId);
  const [customUrl, setCustomUrl] = useState(
    config.presetId === PRESET_IDS.custom ? config.apiBaseUrl ?? "" : "",
  );

  useEffect(() => {
    setPresetId(config.presetId);
    if (config.presetId === PRESET_IDS.custom) {
      setCustomUrl(config.apiBaseUrl ?? "");
    }
  }, [config]);

  const selectedPreset = DATA_SOURCE_PRESETS.find((p) => p.id === presetId);
  const deployedUrl = getDeployedApiBaseUrl();
  const deployedDisabled = presetId === PRESET_IDS.deployed && !deployedUrl;

  function handlePresetChange(nextId: string) {
    setPresetId(nextId);
    if (nextId !== PRESET_IDS.custom) {
      setCustomUrl("");
    }
  }

  function handleLoad() {
    onLoad(
      presetId,
      presetId === PRESET_IDS.custom ? customUrl : undefined,
    );
  }

  return (
    <div className="data-source-control">
      <label className="data-source-control__label" htmlFor="data-source-preset">
        Data source
      </label>
      <div className="data-source-control__row">
        <select
          id="data-source-preset"
          className="data-source-control__select"
          value={presetId}
          onChange={(e) => handlePresetChange(e.target.value)}
          aria-describedby="data-source-help"
        >
          {DATA_SOURCE_PRESETS.map((preset) => (
            <option
              key={preset.id}
              value={preset.id}
              disabled={
                preset.id === PRESET_IDS.deployed && !deployedUrl
              }
            >
              {preset.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn secondary data-source-control__load"
          onClick={handleLoad}
          disabled={deployedDisabled}
        >
          Load data
        </button>
      </div>
      {presetId === PRESET_IDS.custom ? (
        <input
          type="url"
          className="data-source-control__input"
          placeholder="https://api.example.com"
          value={customUrl}
          onChange={(e) => setCustomUrl(e.target.value)}
          aria-label="Custom API base URL"
        />
      ) : null}
      {deployedDisabled ? (
        <p className="data-source-control__hint" id="data-source-help">
          Deployed API requires VITE_PRAXIS_API_BASE_URL at build time.
        </p>
      ) : (
        <p className="data-source-control__hint" id="data-source-help">
          {selectedPreset?.helpText}
          {" "}
          Dashboard reads candidates via candidate-api-v1 — not DynamoDB or PostgreSQL directly.
        </p>
      )}
    </div>
  );
}
