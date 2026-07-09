declare module "mammoth" {
  export function extractRawText(options: {
    path?: string;
    buffer?: Buffer;
  }): Promise<{ value: string; messages: string[] }>;
}
