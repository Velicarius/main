// Типы для работы с Ollama API
// Зачем: Типизация данных от Ollama для безопасности и автодополнения

export type OllamaModel = {
  name: string;
  size?: number;
  family?: string;
  modified?: string;
};

export type InstalledResponse = {
  models: OllamaModel[];
};

export type AllowedModel = {
  tag: string;
  label: string;
};

export type AllowedResponse = {
  allowed: AllowedModel[];
};

export type LLMResponse = {
  success: boolean;
  model: string;
  response: string;
  raw_response?: string;
  error?: string;
  tokens_used?: number;
};

export type PullModelRequest = {
  tag: string;
};

export type PullModelResponse = {
  success: boolean;
  message: string;
  error?: string;
};
