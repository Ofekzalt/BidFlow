import type { ReactNode } from "react";

import { cx } from "@/lib/cx";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

import styles from "./Field.module.css";

type FieldProps = {
  label: string;
  htmlFor: string;
  error?: string;
  children: ReactNode;
  className?: string;
};

export function Field({ label, htmlFor, error, children, className }: FieldProps) {
  return (
    <Stack gap="sm" className={cx(styles.field, className)}>
      <label className={styles.label} htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? (
        <Text variant="caption" className={styles.error}>
          {error}
        </Text>
      ) : null}
    </Stack>
  );
}
