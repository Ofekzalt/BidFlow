import {
  createAuctionRequestDto,
  patchAuctionRequestDto,
} from "@/dto/auction.dto";
import { datetimeLocalToIso } from "@/format/time";

export type AuctionDraftFormValues = {
  title: string;
  description: string;
  startingPriceDollars: string;
  startTime: string;
  endTime: string;
};

export function buildCreateAuctionBody(values: AuctionDraftFormValues) {
  const startingPriceDollars = Number(values.startingPriceDollars);
  return {
    title: values.title,
    description: values.description,
    starting_price_cents: Math.round(startingPriceDollars * 100),
    start_time: datetimeLocalToIso(values.startTime),
    end_time: datetimeLocalToIso(values.endTime),
  };
}

export function buildPatchAuctionBody(values: AuctionDraftFormValues) {
  const startingPriceDollars = Number(values.startingPriceDollars);
  return {
    title: values.title,
    description: values.description,
    starting_price_cents: Math.round(startingPriceDollars * 100),
    start_time: datetimeLocalToIso(values.startTime),
    end_time: datetimeLocalToIso(values.endTime),
  };
}

export function validateCreateAuction(values: AuctionDraftFormValues) {
  return createAuctionRequestDto.safeParse(buildCreateAuctionBody(values));
}

export function validatePatchAuction(values: AuctionDraftFormValues) {
  return patchAuctionRequestDto.safeParse(buildPatchAuctionBody(values));
}

export function isoToDatetimeLocal(iso: string) {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
