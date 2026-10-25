import { z } from "zod";

import { MAX_CENTS } from "@/constants/auction.constants";

export const uuidDto = z.uuid();

export const isoDateTimeDto = z.iso.datetime();

export const centsDto = z.number().int().min(1).max(MAX_CENTS);

export const apiProblemDetailDto = z.object({
  detail: z.string(),
});

export const apiValidationIssueDto = z.object({
  loc: z.array(z.union([z.string(), z.number()])),
  msg: z.string(),
  type: z.string(),
});

export const apiValidationDetailDto = z.object({
  detail: z.array(apiValidationIssueDto),
});
