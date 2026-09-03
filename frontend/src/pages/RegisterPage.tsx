import type { FormEvent } from "react";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { register } from "@/api/auth.api";
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

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

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
      await register(parsed.data);
      navigate("/login", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(authFieldErrors(error));
      } else {
        setFieldErrors({ form: "Unable to create account." });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <Stack gap="lg" className={styles.card}>
        <Stack gap="sm">
          <Text variant="title">Create your account</Text>
          <Text muted>
            Register to bid and sell. JWT is stored in localStorage for this
            demo.
          </Text>
        </Stack>

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            {fieldErrors.form ? (
              <p className={styles.formError}>{fieldErrors.form}</p>
            ) : null}
            <Field label="Email" htmlFor="register-email" error={fieldErrors.email}>
              <Input
                id="register-email"
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
              htmlFor="register-password"
              error={fieldErrors.password}
            >
              <Input
                id="register-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
              />
            </Field>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating account..." : "Create account"}
            </Button>
          </Stack>
        </form>

        <div className={styles.footer}>
          <span>Already registered?</span>
          <Link className={styles.link} to="/login">
            Sign in
          </Link>
        </div>
      </Stack>
    </div>
  );
}
