import type { HTMLAttributes } from "react";

import { cx } from "@/lib/cx";

import styles from "./Stack.module.css";

type StackDirection = "row" | "column";
type StackGap = "sm" | "md" | "lg";
type StackAlign = "start" | "center" | "end" | "stretch";
type StackJustify = "start" | "center" | "end" | "space-between";

type StackProps = HTMLAttributes<HTMLDivElement> & {
  direction?: StackDirection;
  gap?: StackGap;
  align?: StackAlign;
  justify?: StackJustify;
};

const gapClass: Record<StackGap, string> = {
  sm: styles.gapSm,
  md: styles.gapMd,
  lg: styles.gapLg,
};

const alignClass: Record<StackAlign, string> = {
  start: styles.alignStart,
  center: styles.alignCenter,
  end: styles.alignEnd,
  stretch: styles.alignStretch,
};

const justifyClass: Record<StackJustify, string> = {
  start: styles.justifyStart,
  center: styles.justifyCenter,
  end: styles.justifyEnd,
  "space-between": styles.justifyBetween,
};

export function Stack({
  direction = "column",
  gap = "md",
  align = "stretch",
  justify = "start",
  className,
  ...props
}: StackProps) {
  return (
    <div
      className={cx(
        styles.stack,
        direction === "row" ? styles.row : styles.column,
        gapClass[gap],
        alignClass[align],
        justifyClass[justify],
        className,
      )}
      {...props}
    />
  );
}
