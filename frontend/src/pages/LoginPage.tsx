import type { FormEvent } from "react";
import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { login } from "@/api/auth.api";
import { useAuth } from "@/auth/useAuth";
import { ApiError, authFieldErrors } from "@/lib/apiError";
import { zodFieldErrors } from "@/lib/zodFieldErrors";
import { authCredentialsDto } from "@/dto/auth.dto";
import { Button } from "@/ui/Button";
import { Field } from "@/ui/Field";
import { Input } from "@/ui/Input";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

import styles from "./AuthPage.module.css";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const from =
    (location.state as { from?: string } | null)?.from ?? "/";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});

    const parsed = authCredentialsDto.safeParse({ email, password });
    if (!parsed.success) {
      setFieldErrors(zodFieldErrors(parsed.error));
      return;
    }

    setSubmitting(true);

    try {
      const response = await login(parsed.data);
      signIn(response.access_token);
      navigate(from, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(authFieldErrors(error));
      } else {
        setFieldErrors({ form: "Unable to sign in." });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <Stack gap="lg" className={styles.card}>
        <Stack gap="sm">
          <Text variant="title">Sign in to BidFlow</Text>
          <Text muted>
            Access auctions, place bids, and manage payment methods through Kong.
          </Text>
        </Stack>

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            {fieldErrors.form ? (
              <p className={styles.formError}>{fieldErrors.form}</p>
            ) : null}
            <Field label="Email" htmlFor="login-email" error={fieldErrors.email}>
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </Field>
            <Field
              label="Password"
              htmlFor="login-password"
              error={fieldErrors.password}
            >
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </Stack>
        </form>

        <div className={styles.footer}>
          <span>No account?</span>
          <Link className={styles.link} to="/register">
            Create one
          </Link>
        </div>
      </Stack>
    </div>
  );
}
