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

import { beforeEach, describe, expect, it } from 'vitest';
import { USER_PREFERENCES_STORAGE_KEY } from '~/constants';
import { EN_TRANSLATIONS, FR_TRANSLATIONS } from '~/lib/i18n';
import { getRuntimeTranslationTable } from '~/lib/runtime-translations';
import { UILanguage } from '~/types';

describe('runtime-translations', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it('returns English translations by default when no preference is stored', () => {
    expect(getRuntimeTranslationTable()).toBe(EN_TRANSLATIONS);
  });

  it('returns French translations when session user preferences language is French', () => {
    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.French })
    );

    expect(getRuntimeTranslationTable()).toBe(FR_TRANSLATIONS);
  });

  it('falls back to English when user preferences payload is malformed', () => {
    sessionStorage.setItem(USER_PREFERENCES_STORAGE_KEY, '{invalid_json}');

    expect(getRuntimeTranslationTable()).toBe(EN_TRANSLATIONS);
  });

  it('falls back to English when stored language is invalid', () => {
    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: 'de' })
    );

    expect(getRuntimeTranslationTable()).toBe(EN_TRANSLATIONS);
  });

  it('ignores local storage preferences when session preferences are missing', () => {
    localStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.French })
    );

    expect(getRuntimeTranslationTable()).toBe(EN_TRANSLATIONS);
  });
});
