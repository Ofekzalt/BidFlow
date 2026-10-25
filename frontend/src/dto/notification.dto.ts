import { z } from "zod";

import { isoDateTimeDto, uuidDto } from "@/dto/common.dto";

export const notificationResponseDto = z.object({
  id: uuidDto,
  type: z.string(),
  payload: z.record(z.string(), z.unknown()),
  created_at: isoDateTimeDto,
});

export const notificationListDto = z.array(notificationResponseDto);
