import type { z } from 'zod';

import type { severitySchema } from '../tool-contracts.js';

export type FailureDetails = {
  ruleId: string;
  severity: z.infer<typeof severitySchema>;
  message: string;
  suggestion: string;
  evidencePath: string;
  evidenceExcerpt?: string;
};

export class InspectionFailure extends Error {
  readonly details: FailureDetails;

  constructor(details: FailureDetails) {
    super(details.message);
    this.name = 'InspectionFailure';
    this.details = details;
  }
}
