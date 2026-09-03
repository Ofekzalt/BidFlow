import type { InputHTMLAttributes } from "react";

import { cx } from "@/lib/cx";

import styles from "./Input.module.css";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: InputProps) {
  return <input className={cx(styles.input, className)} {...props} />;
}
