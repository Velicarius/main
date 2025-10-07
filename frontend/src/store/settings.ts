import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface UserSettings {
  // AI Model settings - Insights
  insightsAiModel: string;
  insightsAiProvider: 'openai' | 'ollama';
  
  // AI Model settings - News
  newsAiModel: string;
  newsAiProvider: 'openai' | 'ollama';
  
  // UI preferences
  darkMode: boolean;
  autoRefresh: boolean;
  notifications: boolean;
  
  // Other settings
  language: string;
  currency: string;
}

interface SettingsStore {
  settings: UserSettings;
  updateSetting: <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => void;
  resetSettings: () => void;
}

const defaultSettings: UserSettings = {
  // Default to local Llama models
  insightsAiModel: 'llama3.1:8b',
  insightsAiProvider: 'ollama',
  newsAiModel: 'llama3.1:8b',
  newsAiProvider: 'ollama',
  
  // UI defaults
  darkMode: true,
  autoRefresh: false,
  notifications: true,
  
  // Other defaults
  language: 'en',
  currency: 'USD',
};

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      
      updateSetting: (key, value) =>
        set((state) => ({
          settings: {
            ...state.settings,
            [key]: value,
          },
        })),
      
      resetSettings: () =>
        set({
          settings: defaultSettings,
        }),
    }),
    {
      name: 'user-settings',
      version: 2, // Increment version for migration
    }
  )
);
