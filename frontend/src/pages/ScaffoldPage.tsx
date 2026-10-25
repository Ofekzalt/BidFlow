import { Link } from "react-router-dom";

import { useAuth } from "@/auth/useAuth";
import { Badge } from "@/ui/Badge";
import { Button } from "@/ui/Button";
import { Card } from "@/ui/Card";
import { Dialog } from "@/ui/Dialog";
import { Input } from "@/ui/Input";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";
import { useToast } from "@/ui/Toast";

import styles from "./ScaffoldPage.module.css";

export function ScaffoldPage() {
  const { showToast } = useToast();
  const { user, signOut } = useAuth();

  return (
    <Stack gap="lg" className={styles.page}>
      <Stack gap="sm">
        <Text variant="title">BidFlow</Text>
        <Text muted>
          Signed in as {user?.email || user?.id}. API calls go through Kong at{" "}
          {import.meta.env.VITE_API_BASE_URL}.
        </Text>
      </Stack>

      <Card>
        <Stack gap="md">
          <Stack direction="row" gap="sm" align="center" justify="space-between">
            <Stack direction="row" gap="sm" align="center">
              <Badge tone="accent">OPEN</Badge>
              <Badge tone="neutral">DRAFT</Badge>
            </Stack>
            <Stack direction="row" gap="sm" align="center">
              <Link to="/register">Register</Link>
              <Button variant="secondary" type="button" onClick={signOut}>
                Sign out
              </Button>
            </Stack>
          </Stack>
          <Input placeholder="you@example.com" aria-label="Email" />
          <Stack direction="row" gap="sm">
            <Button
              type="button"
              onClick={() => showToast({ title: "Saved", type: "success" })}
            >
              Show toast
            </Button>
            <Dialog.Root>
              <Dialog.Trigger render={<Button variant="secondary" type="button" />}>
                Open dialog
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Backdrop />
                <Dialog.Popup>
                  <Dialog.Title>Dialog ready</Dialog.Title>
                  <Dialog.Description>
                    Base UI behavior with CSS Modules styling.
                  </Dialog.Description>
                  <Dialog.Close render={<Button type="button" />}>Close</Dialog.Close>
                </Dialog.Popup>
              </Dialog.Portal>
            </Dialog.Root>
          </Stack>
        </Stack>
      </Card>
    </Stack>
  );
}
