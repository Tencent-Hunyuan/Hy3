function findAllOccurrences(haystack: string, needle: string): number[] {
  const indices: number[] = [];
  let idx = haystack.indexOf(needle);
  while (idx !== -1) {
    indices.push(idx);
    idx = haystack.indexOf(needle, idx + 1);
  }
  return indices;
}

/**
 * Locates a module's section within the full textbook text using LLM-provided
 * verbatim anchors, then slices it out. Matching is done on whitespace-normalized
 * text (PDF extraction produces inconsistent line breaks/spacing) — both the
 * search and the slice happen on the same normalized copy, so offsets stay
 * consistent; the cost is losing exact original whitespace/paragraph breaks,
 * which doesn't affect factual content fed back into the model.
 *
 * A chapter heading can appear more than twice — once in the table of
 * contents, once at the real chapter start, and again as a running header
 * repeated on every page of that chapter. With more than two occurrences,
 * neither "first" nor "last" reliably lands on the real heading (last might
 * land on a running header near the chapter's *end*, e.g. in a problem set).
 *
 * `hintIndex` — an approximate character offset in `fullText` for where the
 * caller expects this anchor to actually be (e.g. which chunk it was found
 * scanning) — resolves this by picking the occurrence closest to it. Without
 * a hint, this falls back to the last-occurrence heuristic (correct when the
 * only duplicate is the ToC entry, which precedes the real heading).
 *
 * Returns null if startAnchor can't be found — callers should fall back to
 * sending the whole textbook for that module rather than treating this as fatal.
 */
export function sliceSection(
  fullText: string,
  startAnchor: string,
  endAnchor?: string,
  hintIndex?: number,
): string | null {
  const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();

  const normFull = normalize(fullText);
  const normStart = normalize(startAnchor);
  if (!normStart) return null;

  let startIdx: number;
  if (hintIndex !== undefined && fullText.length > 0) {
    const occurrences = findAllOccurrences(normFull, normStart);
    if (occurrences.length === 0) return null;
    // Normalization only removes whitespace, so scaling the hint by the same
    // length ratio keeps it a good-enough estimate for picking among
    // occurrences that are typically many pages apart.
    const scaledHint = (hintIndex / fullText.length) * normFull.length;
    startIdx = occurrences.reduce((closest, cur) =>
      Math.abs(cur - scaledHint) < Math.abs(closest - scaledHint) ? cur : closest
    );
  } else {
    startIdx = normFull.lastIndexOf(normStart);
    if (startIdx === -1) return null;
  }

  let endIdx = normFull.length;
  const normEnd = endAnchor ? normalize(endAnchor) : '';
  if (normEnd) {
    const foundEnd = normFull.indexOf(normEnd, startIdx + normStart.length);
    if (foundEnd !== -1) endIdx = foundEnd;
  }

  const sliced = normFull.slice(startIdx, endIdx).trim();
  return sliced || null;
}

/**
 * Removes probable Table-of-Contents blocks before showing text to Hy3 for
 * chapter/module extraction. A TOC entry ("2-3 Data Model Basic Building
 * Blocks 36") is a short phrase glued to a page number, and real TOCs pack
 * many of these close together — which looks exactly like a clean heading to
 * a model scanning for chapter starts, so it gets picked as the anchor
 * instead of the real, later heading. This only affects what's *sent* for
 * this one call; the material's stored content (used for the actual slicing)
 * is untouched, so anchors found in the surviving text still resolve
 * correctly against it.
 *
 * Heuristic, not exact — it doesn't need to be. It only needs to reduce how
 * often the model has something ToC-shaped to grab instead of the real thing.
 */
export function stripLikelyTableOfContents(text: string): string {
  // A "TOC-entry-ish" run: a short phrase ending in a 1–4 digit page number.
  const entryPattern = /[A-Z][\w'&()/,.-]*(?:\s+[A-Za-z0-9'&()/,.-]+){0,12}\s\d{1,4}(?=\s|$)/g;
  const matches = [...text.matchAll(entryPattern)];
  if (matches.length < 8) return text; // not enough signal to call it a TOC

  const MIN_CLUSTER = 6;
  const GAP_LIMIT = 40; // max chars between entries to still count as the same dense run
  const clusters: { start: number; end: number }[] = [];
  let clusterStart = matches[0].index!;
  let clusterEnd = matches[0].index! + matches[0][0].length;
  let count = 1;

  for (let i = 1; i < matches.length; i++) {
    const m = matches[i];
    const gap = m.index! - clusterEnd;
    if (gap <= GAP_LIMIT) {
      clusterEnd = m.index! + m[0].length;
      count++;
    } else {
      if (count >= MIN_CLUSTER) clusters.push({ start: clusterStart, end: clusterEnd });
      clusterStart = m.index!;
      clusterEnd = m.index! + m[0].length;
      count = 1;
    }
  }
  if (count >= MIN_CLUSTER) clusters.push({ start: clusterStart, end: clusterEnd });
  if (clusters.length === 0) return text;

  let result = '';
  let cursor = 0;
  for (const c of clusters) {
    result += text.slice(cursor, c.start);
    result += '\n[… table of contents omitted — these are page listings, not real chapter starts …]\n';
    cursor = c.end;
  }
  result += text.slice(cursor);
  return result;
}
