import sharp from "sharp";

export async function svgToPng(svg: string, width?: number, height?: number): Promise<Buffer> {
  const pipeline = sharp(Buffer.from(svg, "utf-8"));

  if (width || height) {
    pipeline.resize(width, height, {
      fit: "contain",
      background: { r: 255, g: 255, b: 255, alpha: 0 },
    });
  }

  return pipeline.png().toBuffer();
}
