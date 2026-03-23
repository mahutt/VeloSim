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

import { Loader2 } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import usePreferences from '~/hooks/use-preferences';
import type { UILanguage } from '~/types';
import { Field, FieldGroup, FieldLabel } from './ui/field';
import { Button } from './ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

interface PreferencesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function PreferencesDialog({
  open,
  onOpenChange,
}: PreferencesDialogProps) {
  const { language, setLanguagePreference, saving, t } = usePreferences();
  const [selectedLanguage, setSelectedLanguage] =
    useState<UILanguage>(language);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setSelectedLanguage(language);
    setErrorMessage(null);
  }, [open, language]);

  const formId = 'form-user-preferences';

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);

    try {
      await setLanguagePreference(selectedLanguage);
      onOpenChange(false);
    } catch {
      setErrorMessage(t.preferences.saveError);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-106.25">
        <form id={formId} onSubmit={onSubmit}>
          <DialogHeader>
            <DialogTitle>{t.preferences.title}</DialogTitle>
            <DialogDescription>{t.preferences.description}</DialogDescription>
          </DialogHeader>

          <FieldGroup className="py-4">
            <Field>
              <FieldLabel htmlFor="preferences-language-select">
                {t.preferences.language.label}
              </FieldLabel>
              <select
                id="preferences-language-select"
                value={selectedLanguage}
                onChange={(event) =>
                  setSelectedLanguage(event.target.value as UILanguage)
                }
                disabled={saving}
                className="border-input bg-background h-9 w-full rounded-md border px-3 py-1 text-sm"
              >
                <option value="en">{t.preferences.language.english}</option>
                <option value="fr">{t.preferences.language.french}</option>
              </select>
              <p className="text-muted-foreground text-xs mt-2">
                {t.preferences.language.help}
              </p>
            </Field>

            {errorMessage && (
              <p className="text-destructive text-sm">{errorMessage}</p>
            )}
          </FieldGroup>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={saving}>
                {t.common.cancel}
              </Button>
            </DialogClose>
            <Button type="submit" form={formId} disabled={saving}>
              {t.common.save}
              {saving && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
