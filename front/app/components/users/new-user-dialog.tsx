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

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';
import type { User } from '~/types';
import { Input } from '~/components/ui/input';
import { Button } from '~/components/ui/button';
import z from 'zod';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import api from '~/api';
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '~/components/ui/field';
import { useEffect, useMemo, useState } from 'react';
import { Alert, AlertTitle } from '~/components/ui/alert';
import { AlertCircleIcon, CheckCircle2Icon, Loader2 } from 'lucide-react';
import { Checkbox } from '~/components/ui/checkbox';
import axios from 'axios';
import usePreferences from '~/hooks/use-preferences';
import type { TranslationSchema } from '~/lib/i18n';

type NewUserFormValues = {
  username: string;
  password: string;
  is_admin: boolean;
  is_enabled: boolean;
};

const createNewUserFormSchema = (t: TranslationSchema) =>
  z.object({
    username: z
      .string()
      .min(1, t.users.validation.usernameMin)
      .max(100, t.users.validation.usernameMax),
    password: z.string().min(1, t.users.validation.passwordMin),
    is_admin: z.boolean(),
    is_enabled: z.boolean(),
  });

export default function NewUserDialog({
  open,
  onOpenChange,
  onAddUser,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAddUser: (u: User) => void;
}) {
  const { t } = usePreferences();
  const [message, setMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);
  const newUserFormSchema = useMemo(() => createNewUserFormSchema(t), [t]);

  const formId = `form-new-user`;
  const usernameFieldId = `${formId}-username`;
  const passwordFieldId = `${formId}-password`;
  const isAdminFieldId = `${formId}-is-admin`;
  const isEnabledFieldId = `${formId}-is-enabled`;

  const newUserForm = useForm<NewUserFormValues>({
    resolver: zodResolver(newUserFormSchema),
    defaultValues: {
      username: '',
      password: '',
      is_admin: false,
      is_enabled: true,
    },
  });
  const { isSubmitting } = newUserForm.formState;

  async function onSubmit(data: NewUserFormValues) {
    setMessage(null);
    try {
      const response = await api.post<User>(`/users/create`, data);
      onAddUser(response.data);
      setMessage({ type: 'success', text: t.users.dialog.success });
      newUserForm.reset();
    } catch (e) {
      console.error('New user error', e);
      if (axios.isAxiosError(e) && e.response?.data?.detail) {
        setMessage({ type: 'error', text: e.response.data.detail });
      } else {
        setMessage({ type: 'error', text: t.users.dialog.genericError });
      }
    }
  }

  useEffect(() => {
    if (!open) {
      setMessage(null);
      newUserForm.reset();
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <form id={formId} onSubmit={newUserForm.handleSubmit(onSubmit)}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t.users.dialog.createTitle}</DialogTitle>
            <DialogDescription>
              {t.users.dialog.createDescription}
              <br />
            </DialogDescription>
          </DialogHeader>
          {message && <NewUserFormAlert message={message} />}
          <FieldGroup>
            <Controller
              name="username"
              control={newUserForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={usernameFieldId}>
                    {t.users.dialog.usernameLabel}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={usernameFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder={t.users.dialog.usernamePlaceholder}
                    autoComplete="off"
                    disabled={isSubmitting}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Controller
              name="password"
              control={newUserForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={passwordFieldId}>
                    {t.users.dialog.passwordLabel}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={passwordFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder={t.users.dialog.passwordPlaceholder}
                    autoComplete="off"
                    type="password"
                    disabled={isSubmitting}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Controller
              name="is_admin"
              control={newUserForm.control}
              render={({ field, fieldState }) => (
                <Field
                  data-invalid={fieldState.invalid}
                  orientation="horizontal"
                >
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    id={isAdminFieldId}
                    aria-invalid={fieldState.invalid}
                    disabled={isSubmitting}
                  />
                  <FieldLabel htmlFor={isAdminFieldId}>
                    {t.users.dialog.adminLabel}
                  </FieldLabel>
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Controller
              name="is_enabled"
              control={newUserForm.control}
              render={({ field, fieldState }) => (
                <Field
                  data-invalid={fieldState.invalid}
                  orientation="horizontal"
                >
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    id={isEnabledFieldId}
                    aria-invalid={fieldState.invalid}
                    disabled={isSubmitting}
                  />
                  <FieldLabel htmlFor={isEnabledFieldId}>
                    {t.users.dialog.enabledLabel}
                  </FieldLabel>

                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={isSubmitting}>
                {t.users.dialog.close}
              </Button>
            </DialogClose>
            <Button type="submit" form={formId} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin" />}
              {t.users.dialog.create}
            </Button>
          </DialogFooter>
        </DialogContent>
      </form>
    </Dialog>
  );
}

function NewUserFormAlert({
  message,
}: {
  message: { type: 'success' | 'error'; text: string };
}) {
  const success = message.type === 'success';
  return (
    <Alert variant={success ? 'default' : 'destructive'}>
      {success ? <CheckCircle2Icon /> : <AlertCircleIcon />}
      <AlertTitle>{message.text}</AlertTitle>
    </Alert>
  );
}
