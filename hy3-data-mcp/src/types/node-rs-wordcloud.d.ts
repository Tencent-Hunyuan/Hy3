declare module "node-rs-wordcloud" {
  export type WordCloudItem = [string, number];

  export interface WordCloudOptions {
    list: WordCloudItem[];
    fontFamily?: string;
    fontWeight?: string | ((word: string, weight: number, fontSize: number) => string);
    color?:
      | string
      | ((
          word: string,
          weight: number,
          fontSize: number,
          distance: number,
          theta: number
        ) => string);
    backgroundColor?: string;
    minSize?: number;
    sizeRange?: [number, number];
    gridSize?: number;
    drawOutOfBound?: boolean;
    shrinkToFit?: boolean;
    origin?: [number, number] | null;
    drawMask?: boolean;
    maskColor?: string;
    maskGapWidth?: number;
    abortThreshold?: number;
    abort?: () => void;
    rotationRange?: [number, number];
    rotationSteps?: number;
    shuffle?: boolean;
    rotateRatio?: number;
    shape?: string | ((theta: number) => number);
    ellipticity?: number;
  }

  export interface WordCloudInstance {
    draw(): void;
    updateList(list: WordCloudItem[]): void;
  }

  export type WordCloudRenderer = (
    element: unknown,
    options: WordCloudOptions
  ) => WordCloudInstance;

  type CreateCanvas = (width?: number, height?: number) => unknown;

  const factory: (createCanvas?: CreateCanvas) => WordCloudRenderer;
  export default factory;
}
