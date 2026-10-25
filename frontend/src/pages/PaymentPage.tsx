import { Elements } from "@stripe/react-stripe-js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  createSetupIntent,
  deletePaymentMethod,
  listPaymentMethods,
} from "@/api/payments.api";
import {
  PAYMENT_METHOD_POLL_DURATION_MS,
  PAYMENT_METHOD_POLL_INTERVAL_MS,
} from "@/constants/payment.constants";
import { PaymentSetupForm } from "@/features/payments/PaymentSetupForm";
import { stripePromise } from "@/lib/stripe";
import { paymentKeys } from "@/queries/keys";
import { Button } from "@/ui/Button";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";
import { useToast } from "@/ui/Toast";

import styles from "./PaymentPage.module.css";

export function PaymentPage() {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [pollUntilMs, setPollUntilMs] = useState<number | null>(null);

  const setupIntentMutation = useMutation({
    mutationFn: createSetupIntent,
    onSuccess: (response) => {
      setClientSecret(response.client_secret);
    },
    onError: () => {
      showToast({
        title: "Setup failed",
        description: "Unable to start payment method setup.",
        type: "error",
      });
    },
  });

  const methodsQuery = useQuery({
    queryKey: paymentKeys.methods(),
    queryFn: listPaymentMethods,
    refetchInterval: pollUntilMs && Date.now() < pollUntilMs
      ? PAYMENT_METHOD_POLL_INTERVAL_MS
      : false,
  });

  const deleteMutation = useMutation({
    mutationFn: deletePaymentMethod,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: paymentKeys.methods() });
      showToast({ title: "Payment method removed", type: "success" });
    },
    onError: () => {
      showToast({
        title: "Delete failed",
        description: "Unable to remove payment method.",
        type: "error",
      });
    },
  });

  useEffect(() => {
    if (!clientSecret) {
      setupIntentMutation.mutate();
    }
  }, []);

  function handleSetupComplete() {
    setPollUntilMs(Date.now() + PAYMENT_METHOD_POLL_DURATION_MS);
    showToast({
      title: "Card saved",
      description: "Waiting for payment method readiness...",
      type: "success",
    });
    void queryClient.invalidateQueries({ queryKey: paymentKeys.methods() });
    setupIntentMutation.mutate();
  }

  if (!stripePromise) {
    return (
      <Text muted>
        Set VITE_STRIPE_PUBLISHABLE_KEY to enable payment method setup.
      </Text>
    );
  }

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <Text variant="title">Payment methods</Text>
        <Text muted>
          Save a card to bid on auctions. Only the publishable Stripe key is
          used in the browser.
        </Text>
      </Stack>

      <Card>
        <Stack gap="md">
          <Text variant="heading">Add payment method</Text>
          {clientSecret ? (
            <div className={styles.stripeBox}>
              <Elements
                stripe={stripePromise}
                options={{
                  clientSecret,
                  appearance: { theme: "stripe" },
                }}
              >
                <PaymentSetupForm onComplete={handleSetupComplete} />
              </Elements>
            </div>
          ) : (
            <Text muted>Preparing Stripe setup...</Text>
          )}
        </Stack>
      </Card>

      <Card>
        <Stack gap="md">
          <Text variant="heading">Saved methods</Text>
          {methodsQuery.isLoading ? (
            <Text muted>Loading payment methods...</Text>
          ) : null}
          {methodsQuery.data && methodsQuery.data.length === 0 ? (
            <Text muted>No saved payment methods yet.</Text>
          ) : null}
          <div className={styles.list}>
            {methodsQuery.data?.map((method) => (
              <div key={method.id} className={styles.method}>
                <Stack gap="sm">
                  <Text variant="caption">
                    {method.stripe_payment_method_id}
                  </Text>
                  {method.is_default ? (
                    <Text variant="caption" muted>
                      Default
                    </Text>
                  ) : null}
                </Stack>
                <Button
                  variant="secondary"
                  type="button"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(method.id)}
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </Stack>
      </Card>
    </Stack>
  );
}
