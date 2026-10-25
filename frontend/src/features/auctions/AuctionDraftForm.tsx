import type { FormEvent } from "react";
import { useState } from "react";

import type {
  CreateAuctionRequest,
  PatchAuctionRequest,
} from "@/api/auctions.api";
import {
  type AuctionDraftFormValues,
  validateCreateAuction,
  validatePatchAuction,
} from "@/features/auctions/AuctionDraftForm.helpers";
import { zodFieldErrors } from "@/lib/zodFieldErrors";
import { Button } from "@/ui/Button";
import { Field } from "@/ui/Field";
import { Input } from "@/ui/Input";
import { Stack } from "@/ui/Stack";

import styles from "@/pages/AuctionFormPage.module.css";

export type { AuctionDraftFormValues } from "@/features/auctions/AuctionDraftForm.helpers";
export {
  isoToDatetimeLocal,
} from "@/features/auctions/AuctionDraftForm.helpers";

type AuctionDraftFormProps =
  | {
      mode: "create";
      initialValues?: AuctionDraftFormValues;
      submitLabel: string;
      onValidSubmit: (body: CreateAuctionRequest) => Promise<void>;
    }
  | {
      mode: "patch";
      initialValues?: AuctionDraftFormValues;
      submitLabel: string;
      onValidSubmit: (body: PatchAuctionRequest) => Promise<void>;
    };

const emptyValues: AuctionDraftFormValues = {
  title: "",
  description: "",
  startingPriceDollars: "",
  startTime: "",
  endTime: "",
};

export function AuctionDraftForm({
  mode,
  initialValues = emptyValues,
  submitLabel,
  onValidSubmit,
}: AuctionDraftFormProps) {
  const [values, setValues] = useState(initialValues);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function updateField<K extends keyof AuctionDraftFormValues>(
    key: K,
    value: AuctionDraftFormValues[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setFormError(null);

    if (mode === "create") {
      const parsed = validateCreateAuction(values);
      if (!parsed.success) {
        setFieldErrors(zodFieldErrors(parsed.error));
        return;
      }

      setSubmitting(true);

      try {
        await onValidSubmit(parsed.data);
      } catch {
        setFormError("Unable to save auction.");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    const parsed = validatePatchAuction(values);
    if (!parsed.success) {
      setFieldErrors(zodFieldErrors(parsed.error));
      return;
    }

    setSubmitting(true);

    try {
      await onValidSubmit(parsed.data);
    } catch {
      setFormError("Unable to save auction.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        {formError ? <p className={styles.formError}>{formError}</p> : null}
        <Field label="Title" htmlFor="auction-title" error={fieldErrors.title}>
          <Input
            id="auction-title"
            value={values.title}
            onChange={(event) => updateField("title", event.target.value)}
            required
          />
        </Field>
        <Field
          label="Description"
          htmlFor="auction-description"
          error={fieldErrors.description}
        >
          <Input
            id="auction-description"
            value={values.description}
            onChange={(event) => updateField("description", event.target.value)}
            required
          />
        </Field>
        <Field
          label="Starting price (USD)"
          htmlFor="auction-starting-price"
          error={fieldErrors.starting_price_cents}
        >
          <Input
            id="auction-starting-price"
            type="number"
            min={1}
            step={1}
            value={values.startingPriceDollars}
            onChange={(event) =>
              updateField("startingPriceDollars", event.target.value)
            }
            required
          />
        </Field>
        <Field
          label="Start time"
          htmlFor="auction-start-time"
          error={fieldErrors.start_time}
        >
          <Input
            id="auction-start-time"
            type="datetime-local"
            value={values.startTime}
            onChange={(event) => updateField("startTime", event.target.value)}
            required
          />
        </Field>
        <Field
          label="End time"
          htmlFor="auction-end-time"
          error={fieldErrors.end_time}
        >
          <Input
            id="auction-end-time"
            type="datetime-local"
            value={values.endTime}
            onChange={(event) => updateField("endTime", event.target.value)}
            required
          />
        </Field>
        <div className={styles.actions}>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : submitLabel}
          </Button>
        </div>
      </Stack>
    </form>
  );
}
