import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listNotifications } from "@/api/notifications.api";
import {
  EVENT_TYPE_PAYMENT_FAILED,
  EVENT_TYPE_PAYMENT_SUCCEEDED,
} from "@/constants/payment.constants";
import { formatDateTime } from "@/format/time";
import { notificationKeys } from "@/queries/keys";
import { Badge } from "@/ui/Badge";
import { Card } from "@/ui/Card";
import { Stack } from "@/ui/Stack";
import { Text } from "@/ui/Text";

import styles from "./NotificationsPage.module.css";

function notificationTone(type: string) {
  if (type === EVENT_TYPE_PAYMENT_SUCCEEDED) {
    return "success" as const;
  }
  if (type === EVENT_TYPE_PAYMENT_FAILED) {
    return "danger" as const;
  }
  return "neutral" as const;
}

function readAuctionId(payload: Record<string, unknown>) {
  const auctionId = payload.auction_id;
  return typeof auctionId === "string" ? auctionId : null;
}

export function NotificationsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: notificationKeys.list(),
    queryFn: listNotifications,
  });

  return (
    <Stack gap="lg">
      <Stack gap="sm">
        <Text variant="title">Notifications</Text>
        <Text muted>Payment outcomes from closed auctions.</Text>
      </Stack>

      {isLoading ? <Text muted>Loading notifications...</Text> : null}
      {isError ? (
        <p className={styles.error}>Unable to load notifications.</p>
      ) : null}

      <Card>
        {data && data.length === 0 ? (
          <Text muted>No notifications yet.</Text>
        ) : null}
        <div className={styles.list}>
          {data?.map((notification) => {
            const auctionId = readAuctionId(notification.payload);
            return (
              <div key={notification.id} className={styles.item}>
                <Stack gap="sm">
                  <Badge tone={notificationTone(notification.type)}>
                    {notification.type}
                  </Badge>
                  <Text variant="caption" muted>
                    {formatDateTime(notification.created_at)}
                  </Text>
                </Stack>
                {auctionId ? (
                  <Link className={styles.link} to={`/auctions/${auctionId}`}>
                    View auction
                  </Link>
                ) : null}
              </div>
            );
          })}
        </div>
      </Card>
    </Stack>
  );
}
