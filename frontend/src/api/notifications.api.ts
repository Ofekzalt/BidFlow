import type { z } from "zod";

import { notificationListDto, notificationResponseDto } from "@/dto/notification.dto";
import { request } from "@/lib/http";

export type NotificationResponse = z.infer<typeof notificationResponseDto>;

export function listNotifications() {
  return request("/notifications", {
    method: "GET",
    responseDto: notificationListDto,
  });
}
