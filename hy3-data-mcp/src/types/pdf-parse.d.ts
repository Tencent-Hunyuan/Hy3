declare module "pdf2json" {
  import { EventEmitter } from "events";

  interface PDFParserData {
    Pages: Array<{
      Texts: Array<{
        R: Array<{ T: string }>;
      }>;
    }>;
    Meta?: Record<string, unknown>;
  }

  class PDFParser extends EventEmitter {
    constructor();
    loadPDF(filePath: string): void;
    on(event: "pdfParser_dataReady", listener: (data: PDFParserData) => void): this;
    on(event: "pdfParser_dataError", listener: (err: Error) => void): this;
    getRawTextContent(): string;
  }

  export = PDFParser;
}
