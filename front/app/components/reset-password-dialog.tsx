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
import { Input } from './ui/input';
import { Button } from './ui/button';
import useAuth from '~/hooks/use-auth';
import z from 'zod';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import api from '~/api';
import { Field, FieldError, FieldGroup, FieldLabel } from './ui/field';
import { useMemo, useRef, useState } from 'react';
import { Alert, AlertTitle } from './ui/alert';
import { AlertCircleIcon, CheckCircle2Icon, Loader2 } from 'lucide-react';
import usePreferences from '~/hooks/use-preferences';
import type { TranslationSchema } from '~/lib/i18n';

const createUpdatePasswordFormSchema = (t: TranslationSchema) =>
  z
    .object({
      password: z.string().min(1, t.resetPassword.validation.passwordMin),
      confirm: z.string(),
    })
    .refine((data) => data.password === data.confirm, {
      message: t.resetPassword.validation.passwordsDontMatch,
      path: ['confirm'],
    });

type UpdatePasswordFormData = z.infer<
  ReturnType<typeof createUpdatePasswordFormSchema>
>;

export default function ResetPasswordDialog({
  open,
  onOpenChange,
  targetUser,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  targetUser: User;
}) {
  const { user } = useAuth();
  const { t } = usePreferences();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<UpdatePasswordFormMessage | null>(
    null
  );
  const closeDialogTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const title =
    user?.id === targetUser.id
      ? t.resetPassword.title.self
      : `${t.resetPassword.title.other} ${targetUser.username}`;

  const updatePasswordFormSchema = useMemo(
    () => createUpdatePasswordFormSchema(t),
    [t]
  );

  const formId = `form-update-password-${targetUser.id}`;
  const passwordFieldId = `${formId}-password`;
  const confirmFieldId = `${formId}-confirm`;

  const updatePasswordForm = useForm<UpdatePasswordFormData>({
    resolver: zodResolver(updatePasswordFormSchema),
    defaultValues: {
      password: '',
      confirm: '',
    },
  });

  async function onSubmit(data: UpdatePasswordFormData) {
    setMessage(null);
    setLoading(true);
    try {
      await api.put<User>(`/users/${targetUser.id}/password`, {
        password: data.password,
      });
      setMessage('success');
      updatePasswordForm.reset();
      closeDialogTimeoutRef.current = setTimeout(() => {
        onOpenChange(false);
        setMessage(null);
      }, 2000);
    } catch (e) {
      console.error('Reset password error', e);
      setMessage('error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        // If the modal is manually opened or closed,
        // clear the timeout to prevent the modal from closing unexpectedly.
        if (closeDialogTimeoutRef.current) {
          clearTimeout(closeDialogTimeoutRef.current);
          closeDialogTimeoutRef.current = null;
        }
        // Reset form & message state when closing the dialog manually
        if (!newOpen && !loading) {
          updatePasswordForm.reset();
          setMessage(null);
        }
        onOpenChange(newOpen);
      }}
    >
      <DialogContent className="sm:max-w-[425px]">
        <form id={formId} onSubmit={updatePasswordForm.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>
              {t.resetPassword.description}
              <br />
            </DialogDescription>
          </DialogHeader>
          {message && <UpdatePasswordFormAlert message={message} />}
          <FieldGroup className="py-4">
            <Controller
              name="password"
              control={updatePasswordForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={passwordFieldId}>
                    {t.resetPassword.password}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={passwordFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder={t.resetPassword.newPasswordPlaceholder}
                    autoComplete="off"
                    type="password"
                    disabled={loading}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Controller
              name="confirm"
              control={updatePasswordForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={confirmFieldId}>
                    {t.resetPassword.confirmPassword}
                  </FieldLabel>
                  <Input
                    {...field}
                    id={confirmFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder={t.resetPassword.confirmPasswordPlaceholder}
                    autoComplete="off"
                    type="password"
                    disabled={loading}
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
          </FieldGroup>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={loading}>
                {t.common.cancel}
              </Button>
            </DialogClose>
            <Button type="submit" form={formId} disabled={loading}>
              {t.common.update}
              {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

type UpdatePasswordFormMessage = 'success' | 'error';

function UpdatePasswordFormAlert({
  message,
}: {
  message: UpdatePasswordFormMessage;
}) {
  const { t } = usePreferences();
  const success = message === 'success';
  return (
    <Alert variant={success ? 'default' : 'destructive'}>
      {success ? <CheckCircle2Icon /> : <AlertCircleIcon />}
      <AlertTitle>
        {success ? t.resetPassword.success : t.resetPassword.error}
      </AlertTitle>
    </Alert>
  );
}
