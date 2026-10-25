import type { HTMLAttributes } from "react";

import { cx } from "@/lib/cx";

import styles from "./Badge.module.css";

type BadgeTone = "neutral" | "success" | "danger" | "warning" | "accent";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span className={cx(styles.badge, styles[tone], className)} {...props} />
  );
}
