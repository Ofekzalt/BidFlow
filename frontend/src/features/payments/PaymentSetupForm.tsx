import {
  PaymentElement,
  useElements,
  useStripe,
} from "@stripe/react-stripe-js";
import type { FormEvent } from "react";
import { useState } from "react";

import { Button } from "@/ui/Button";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

type PaymentSetupFormProps = {
  onComplete: () => void;
};

export function PaymentSetupForm({ onComplete }: PaymentSetupFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!stripe || !elements) {
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    const result = await stripe.confirmSetup({
      elements,
      redirect: "if_required",
    });

    setSubmitting(false);

    if (result.error) {
      setErrorMessage(result.error.message ?? "Unable to save payment method.");
      return;
    }

    onComplete();
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <PaymentElement />
        {errorMessage ? <Text variant="caption">{errorMessage}</Text> : null}
        <Button type="submit" disabled={!stripe || submitting}>
          {submitting ? "Saving card..." : "Save payment method"}
        </Button>
      </Stack>
    </form>
  );
}
