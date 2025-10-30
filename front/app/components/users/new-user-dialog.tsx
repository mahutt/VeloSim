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
import { useEffect, useState } from 'react';
import { Alert, AlertTitle } from '~/components/ui/alert';
import { AlertCircleIcon, CheckCircle2Icon, Loader2 } from 'lucide-react';
import { Checkbox } from '~/components/ui/checkbox';
import axios from 'axios';

const newUserFormSchema = z.object({
  username: z
    .string()
    .min(1, 'Username must be at least 1 character.')
    .max(100, 'Username must be at most 100 characters.'),
  password: z.string().min(1, 'Password must be at least 1 character.'),
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
  const [message, setMessage] = useState<string | null>(null);

  const formId = `form-new-user`;
  const usernameFieldId = `${formId}-username`;
  const passwordFieldId = `${formId}-password`;
  const isAdminFieldId = `${formId}-is-admin`;
  const isEnabledFieldId = `${formId}-is-enabled`;

  const newUserForm = useForm<z.infer<typeof newUserFormSchema>>({
    resolver: zodResolver(newUserFormSchema),
    defaultValues: {
      username: '',
      password: '',
      is_admin: false,
      is_enabled: true,
    },
  });
  const { isSubmitting } = newUserForm.formState;

  async function onSubmit(data: z.infer<typeof newUserFormSchema>) {
    setMessage(null);
    try {
      const response = await api.post<User>(`/users/create`, data);
      onAddUser(response.data);
      setMessage(newUserFormMessage.Success);
      newUserForm.reset();
    } catch (e) {
      console.error('New user error', e);
      if (axios.isAxiosError(e) && e.response?.data?.detail) {
        setMessage(e.response.data.detail);
      } else {
        setMessage(newUserFormMessage.GenericError);
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
            <DialogTitle>Create new user</DialogTitle>
            <DialogDescription>
              Create a new user by filling out the form below.
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
                  <FieldLabel htmlFor={usernameFieldId}>Username</FieldLabel>
                  <Input
                    {...field}
                    id={usernameFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder="Username"
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
                  <FieldLabel htmlFor={passwordFieldId}>Password</FieldLabel>
                  <Input
                    {...field}
                    id={passwordFieldId}
                    aria-invalid={fieldState.invalid}
                    placeholder="Password"
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
                  <FieldLabel htmlFor={isAdminFieldId}>Admin</FieldLabel>
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
                  <FieldLabel htmlFor={isEnabledFieldId}>Enabled</FieldLabel>

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
                Close
              </Button>
            </DialogClose>
            <Button type="submit" form={formId} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </form>
    </Dialog>
  );
}

enum newUserFormMessage {
  Success = 'User created successfully',
  GenericError = 'Something went wrong',
}

function NewUserFormAlert({ message }: { message: string }) {
  const success = message === newUserFormMessage.Success;
  return (
    <Alert variant={success ? 'default' : 'destructive'}>
      {success ? <CheckCircle2Icon /> : <AlertCircleIcon />}
      <AlertTitle>{message}</AlertTitle>
    </Alert>
  );
}
