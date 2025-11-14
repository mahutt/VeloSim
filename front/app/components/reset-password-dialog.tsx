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
import { useRef, useState } from 'react';
import { Alert, AlertTitle } from './ui/alert';
import { AlertCircleIcon, CheckCircle2Icon, Loader2 } from 'lucide-react';

const updatePasswordFormSchema = z
  .object({
    password: z.string().min(1, 'Password must be at least 1 character.'),
    confirm: z.string(),
  })
  .refine((data) => data.password === data.confirm, {
    message: "Passwords don't match",
    path: ['confirm'],
  });

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
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<UpdatePasswordFormMessage | null>(
    null
  );
  const closeDialogTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const title =
    user?.id === targetUser.id
      ? 'Update your password'
      : `Update password for ${targetUser.username}`;

  const formId = `form-update-password-${targetUser.id}`;
  const passwordFieldId = `${formId}-password`;
  const confirmFieldId = `${formId}-confirm`;

  const updatePasswordForm = useForm<z.infer<typeof updatePasswordFormSchema>>({
    resolver: zodResolver(updatePasswordFormSchema),
    defaultValues: {
      password: '',
      confirm: '',
    },
  });

  async function onSubmit(data: z.infer<typeof updatePasswordFormSchema>) {
    setMessage(null);
    setLoading(true);
    try {
      await api.put<User>(`/users/${targetUser.id}/password`, {
        password: data.password,
      });
      setMessage(UpdatePasswordFormMessage.Success);
      updatePasswordForm.reset();
      closeDialogTimeoutRef.current = setTimeout(() => {
        onOpenChange(false);
        setMessage(null);
      }, 2000);
    } catch (e) {
      console.error('Reset password error', e);
      setMessage(UpdatePasswordFormMessage.Error);
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
      <form id={formId} onSubmit={updatePasswordForm.handleSubmit(onSubmit)}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>
              Enter the same (new) password twice. Click update when you&apos;re
              done.
              <br />
            </DialogDescription>
          </DialogHeader>
          {message && <UpdatePasswordFormAlert message={message} />}
          <FieldGroup>
            <Controller
              name="password"
              control={updatePasswordForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor={passwordFieldId}>Password</FieldLabel>
                  <Input
                    {...field}
                    id={passwordFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder="New password"
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
                    Confirm password
                  </FieldLabel>
                  <Input
                    {...field}
                    id={confirmFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder="Confirm new password"
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
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" form={formId} disabled={loading}>
              Update
              {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
            </Button>
          </DialogFooter>
        </DialogContent>
      </form>
    </Dialog>
  );
}

enum UpdatePasswordFormMessage {
  Success = 'Password updated successfully',
  Error = 'Something went wrong',
}

function UpdatePasswordFormAlert({
  message,
}: {
  message: UpdatePasswordFormMessage;
}) {
  const success = message === UpdatePasswordFormMessage.Success;
  return (
    <Alert variant={success ? 'default' : 'destructive'}>
      {success ? <CheckCircle2Icon /> : <AlertCircleIcon />}
      <AlertTitle>{message}</AlertTitle>
    </Alert>
  );
}
