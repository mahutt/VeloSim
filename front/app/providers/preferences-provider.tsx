/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import api from '~/api';
import { DEFAULT_UI_LANGUAGE, USER_PREFERENCES_STORAGE_KEY } from '~/constants';
import useAuth from '~/hooks/use-auth';
import {
  EN_TRANSLATIONS,
  FR_TRANSLATIONS,
  type TranslationSchema,
} from '~/lib/i18n';
import {
  UILanguage,
  type UserPreferences,
  type UserPreferencesPatch,
} from '~/types';

const DEFAULT_PREFERENCES: UserPreferences = {
  language: DEFAULT_UI_LANGUAGE,
};

const isUiLanguage = (value: unknown): value is UILanguage => {
  return Object.values(UILanguage).includes(value as UILanguage);
};

const getStoredPreferences = (): UserPreferences => {
  const raw = sessionStorage.getItem(USER_PREFERENCES_STORAGE_KEY);
  if (raw == null) {
    return DEFAULT_PREFERENCES;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    if (isUiLanguage(parsed.language)) {
      return { language: parsed.language };
    }
  } catch {
    // Ignore malformed session storage payload.
  }

  return DEFAULT_PREFERENCES;
};

const persistPreferences = (preferences: UserPreferences): void => {
  sessionStorage.setItem(
    USER_PREFERENCES_STORAGE_KEY,
    JSON.stringify(preferences)
  );
};

export interface PreferencesState {
  language: UILanguage;
  preferences: UserPreferences;
  loading: boolean;
  saving: boolean;
  refreshPreferences: () => Promise<void>;
  updatePreferences: (patch: UserPreferencesPatch) => Promise<void>;
  setLanguagePreference: (language: UILanguage) => Promise<void>;
  t: TranslationSchema;
}

export const PreferencesContext = createContext<PreferencesState | undefined>(
  undefined
);

interface PreferencesProviderProps {
  children: ReactNode;
}

export const PreferencesProvider: React.FC<PreferencesProviderProps> = ({
  children,
}) => {
  const { user, loading: authLoading } = useAuth();
  const [preferences, setPreferences] =
    useState<UserPreferences>(getStoredPreferences);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const language = preferences.language;
  const [t, setT] = useState<TranslationSchema>(EN_TRANSLATIONS);

  const refreshPreferences = useCallback(async () => {
    if (user == null) {
      const nextPreferences = getStoredPreferences();
      setPreferences(nextPreferences);
      persistPreferences(nextPreferences);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await api.get<UserPreferences>('/users/me/preferences');
      const nextPreferences = response.data;
      setPreferences(nextPreferences);
      persistPreferences(nextPreferences);
    } catch (error) {
      console.error('Failed to load user preferences', error);
      const nextPreferences = getStoredPreferences();
      setPreferences(nextPreferences);
      persistPreferences(nextPreferences);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  const updatePreferences = useCallback(
    async (patch: UserPreferencesPatch) => {
      if (user == null) {
        return;
      }

      setSaving(true);
      try {
        const response = await api.patch<UserPreferences>(
          '/users/me/preferences',
          patch
        );
        const nextPreferences = response.data;
        setPreferences(nextPreferences);
        persistPreferences(nextPreferences);
      } catch (error) {
        console.error('Failed to update user preferences', error);
        throw error;
      } finally {
        setSaving(false);
      }
    },
    [user?.id]
  );

  const setLanguagePreference = useCallback(
    async (nextLanguage: UILanguage) => {
      await updatePreferences({ language: nextLanguage });
    },
    [updatePreferences]
  );

  useEffect(() => {
    if (authLoading) {
      return;
    }

    void refreshPreferences();
  }, [authLoading, refreshPreferences]);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    if (language === UILanguage.French) {
      setT(FR_TRANSLATIONS);
    } else {
      setT(EN_TRANSLATIONS);
    }
  }, [language]);

  const value: PreferencesState = useMemo(
    () => ({
      language,
      preferences,
      loading,
      saving,
      refreshPreferences,
      updatePreferences,
      setLanguagePreference,
      t,
    }),
    [
      language,
      preferences,
      loading,
      saving,
      refreshPreferences,
      updatePreferences,
      setLanguagePreference,
      t,
    ]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
};
