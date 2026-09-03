import type { HTMLAttributes } from "react";

import { cx } from "@/lib/cx";

import styles from "./Text.module.css";

type TextVariant = "body" | "caption" | "heading" | "title" | "data";

type TextProps = HTMLAttributes<HTMLParagraphElement> & {
  variant?: TextVariant;
  muted?: boolean;
};

const variantClass: Record<TextVariant, string> = {
  title: styles.title,
  heading: styles.heading,
  body: styles.body,
  caption: styles.caption,
  data: styles.data,
};

export function Text({
  variant = "body",
  muted = false,
  className,
  ...props
}: TextProps) {
  return (
    <p
      className={cx(styles.text, variantClass[variant], muted && styles.muted, className)}
      {...props}
    />
  );
}
