import { z } from "zod";

import {
  ERROR_START_BEFORE_END,
  TITLE_MAX_LENGTH,
} from "@/constants/auction.constants";
import { centsDto, isoDateTimeDto, uuidDto } from "@/dto/common.dto";

export const auctionResponseDto = z.object({
  id: uuidDto,
  seller_id: uuidDto,
  title: z.string(),
  description: z.string(),
  starting_price_cents: centsDto,
  current_price_cents: centsDto,
  current_winner_id: uuidDto.nullable(),
  final_amount_cents: centsDto.nullable(),
  winner_id: uuidDto.nullable(),
  status: z.string(),
  start_time: isoDateTimeDto,
  end_time: isoDateTimeDto,
  created_at: isoDateTimeDto,
  updated_at: isoDateTimeDto,
});

export const auctionListDto = z.array(auctionResponseDto);

export const currentBidResponseDto = z.object({
  amount_cents: centsDto,
  bidder_id: uuidDto.nullable(),
});

export const placeBidRequestDto = z.object({
  amount_cents: centsDto,
});

export const bidResponseDto = z.object({
  auction_id: uuidDto,
  bidder_id: uuidDto,
  amount_cents: centsDto,
});

export const createAuctionRequestDto = z
  .object({
    title: z.string().trim().min(1).max(TITLE_MAX_LENGTH),
    description: z.string(),
    starting_price_cents: centsDto,
    start_time: isoDateTimeDto,
    end_time: isoDateTimeDto,
  })
  .refine((value) => value.start_time < value.end_time, {
    message: ERROR_START_BEFORE_END,
    path: ["end_time"],
  });

export const patchAuctionRequestDto = z
  .object({
    title: z.string().trim().min(1).max(TITLE_MAX_LENGTH).optional(),
    description: z.string().optional(),
    starting_price_cents: centsDto.optional(),
    start_time: isoDateTimeDto.optional(),
    end_time: isoDateTimeDto.optional(),
  })
  .refine(
    (value) => {
      if (value.start_time !== undefined && value.end_time !== undefined) {
        return value.start_time < value.end_time;
      }
      return true;
    },
    {
      message: ERROR_START_BEFORE_END,
      path: ["end_time"],
    },
  );
