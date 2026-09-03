import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { ApiError, toDomainErrorCode } from "@/lib/apiError";
import { zodFieldErrors } from "@/lib/zodFieldErrors";
import { placeBidRequestDto } from "@/dto/auction.dto";
import { usePlaceBid } from "@/hooks/usePlaceBid";
import { formatMoney } from "@/format/money";
import { Button } from "@/ui/Button";
import { Field } from "@/ui/Field";
import { Input } from "@/ui/Input";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

type BidFormProps = {
  auctionId: string;
  currentPriceCents: number;
  onDomainError?: (
    code: ReturnType<typeof toDomainErrorCode>,
    message: string,
  ) => void;
};

function createIdempotencyKey() {
  return crypto.randomUUID();
}

export function BidForm({
  auctionId,
  currentPriceCents,
  onDomainError,
}: BidFormProps) {
  const { mutateAsync, isPending } = usePlaceBid(auctionId);
  const [amount, setAmount] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const idempotencyKeyRef = useRef(createIdempotencyKey());
  const lastAmountCentsRef = useRef<number | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setFormError(null);

    const dollars = Number(amount);
    if (!Number.isFinite(dollars)) {
      setFieldErrors({ amount_cents: "Enter a valid whole-dollar amount." });
      return;
    }

    const amountCents = Math.round(dollars * 100);
    const parsed = placeBidRequestDto.safeParse({ amount_cents: amountCents });
    if (!parsed.success) {
      setFieldErrors(zodFieldErrors(parsed.error));
      return;
    }

    if (lastAmountCentsRef.current !== parsed.data.amount_cents) {
      idempotencyKeyRef.current = createIdempotencyKey();
      lastAmountCentsRef.current = parsed.data.amount_cents;
    }

    try {
      await mutateAsync({
        body: parsed.data,
        idempotencyKey: idempotencyKeyRef.current,
      });
      setAmount("");
      lastAmountCentsRef.current = null;
      idempotencyKeyRef.current = createIdempotencyKey();
    } catch (error) {
      if (error instanceof ApiError) {
        const code = toDomainErrorCode(error);
        if (code === "stale_bid") {
          setFieldErrors({ amount_cents: error.detail });
          return;
        }
        if (code !== "unknown") {
          onDomainError?.(code, error.detail);
          return;
        }
        setFormError(error.detail);
        return;
      }
      setFormError("Unable to place bid.");
    }
  }

  const minimumDollars = Math.ceil((currentPriceCents + 1) / 100);

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <Text muted variant="caption">
          Current price is {formatMoney(currentPriceCents)}. Bid at least{" "}
          {formatMoney(minimumDollars * 100)}.
        </Text>
        {formError ? <Text variant="caption">{formError}</Text> : null}
        <Field
          label="Your bid (USD, whole dollars)"
          htmlFor={`bid-amount-${auctionId}`}
          error={fieldErrors.amount_cents}
        >
          <Input
            id={`bid-amount-${auctionId}`}
            type="number"
            min={minimumDollars}
            step={1}
            inputMode="numeric"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder={String(minimumDollars)}
          />
        </Field>
        <Button type="submit" disabled={isPending}>
          {isPending ? "Placing bid..." : "Place bid"}
        </Button>
      </Stack>
    </form>
  );
}
