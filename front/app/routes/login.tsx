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

import { Button } from '~/components/ui/button';
import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, useForm } from 'react-hook-form';
import * as z from 'zod';
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '~/components/ui/field';
import { Input } from '~/components/ui/input';
import type { LoginForAccessTokenResponse } from '~/types';
import axios from 'axios';
import LoginAlert from '~/components/login/login-alert';
import { useState } from 'react';
import useAuth from '~/hooks/use-auth';

export function meta() {
  return [{ title: 'Login' }];
}

const loginFormSchema = z.object({
  username: z
    .string()
    .min(1, 'Username must be at least 1 character.')
    .max(100, 'Username must be at most 100 characters.'),
  password: z.string().min(1, 'Password must be at least 1 character.'),
});

export default function Signin() {
  const { refreshUser, setToken } = useAuth();
  const [responseCode, setResponseCode] = useState<number | null>(null);

  const loginForm = useForm<z.infer<typeof loginFormSchema>>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  });

  async function onSubmit(data: z.infer<typeof loginFormSchema>) {
    const formData = new FormData();
    formData.append('username', data.username);
    formData.append('password', data.password);
    try {
      const response = await axios.post<LoginForAccessTokenResponse>(
        `${import.meta.env.VITE_BACKEND_URL}/api/token`,
        formData
      );
      setToken(response.data.access_token);
      refreshUser();
    } catch (e) {
      console.error('Login error', e);
      if (axios.isAxiosError(e) && e.status) {
        setResponseCode(e.status);
      }
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center">
      <div className="w-sm p-4 m-4 flex flex-col gap-4">
        <img
          src="/logo.png"
          alt="VeloSim Logo"
          className="mx-auto w-16 sm:w-32"
        />
        {responseCode && <LoginAlert code={responseCode} />}
        <form id="form-login" onSubmit={loginForm.handleSubmit(onSubmit)}>
          <FieldGroup>
            <Controller
              name="username"
              control={loginForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="form-login-username">
                    Username
                  </FieldLabel>
                  <Input
                    {...field}
                    id="form-login-username"
                    aria-invalid={fieldState.invalid}
                    placeholder="Username"
                    autoComplete="off"
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Controller
              name="password"
              control={loginForm.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="form-login-password">
                    Password
                  </FieldLabel>
                  <Input
                    {...field}
                    id="form-login-password"
                    aria-invalid={fieldState.invalid}
                    placeholder="Password"
                    autoComplete="off"
                    type="password"
                  />
                  {fieldState.invalid && (
                    <FieldError errors={[fieldState.error]} />
                  )}
                </Field>
              )}
            />
            <Field orientation="horizontal">
              <Button type="submit" form="form-login" className="w-full">
                Log in
              </Button>
            </Field>
          </FieldGroup>
        </form>
      </div>
    </div>
  );
}
