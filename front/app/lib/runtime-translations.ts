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

import { DEFAULT_UI_LANGUAGE, USER_PREFERENCES_STORAGE_KEY } from '~/constants';
import {
  EN_TRANSLATIONS,
  FR_TRANSLATIONS,
  type TranslationSchema,
} from '~/lib/i18n';
import { isUiLanguage } from '~/lib/ui-language';
import { UILanguage, type UserPreferences } from '~/types';

const getStoredLanguage = (): UILanguage => {
  try {
    const rawPreferences = sessionStorage.getItem(USER_PREFERENCES_STORAGE_KEY);
    if (rawPreferences != null) {
      const parsed = JSON.parse(rawPreferences) as UserPreferences;
      if (isUiLanguage(parsed.language)) {
        return parsed.language;
      }
    }
  } catch {
    // Ignore malformed session storage payload.
  }

  return DEFAULT_UI_LANGUAGE;
};

export const getRuntimeTranslationTable = (): TranslationSchema => {
  return getStoredLanguage() === UILanguage.French
    ? FR_TRANSLATIONS
    : EN_TRANSLATIONS;
};
