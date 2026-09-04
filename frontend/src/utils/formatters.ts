/**
 * frontend/src/utils/formatters.ts
 * Formatting utilities for taxonomy category names, pricing labels, and metrics.
 */

/**
 * Transforms raw, concatenated Shopify taxonomy slugs/names into clean,
 * concise, non-repetitive titles suitable for a professional intelligence platform.
 *
 * Examples:
 * - 'orders-and-shipping-shipping-solutions-shipping' -> 'Shipping Solutions (Orders & Shipping)'
 * - 'store-design-site-optimization-seo' -> 'Site Optimization SEO (Store Design)'
 * - 'finding-products-sourcing-options-dropshipping' -> 'Dropshipping & Sourcing (Finding Products)'
 * - 'Advertising   other' -> 'Advertising (Other)'
 */
export function formatCategoryName(rawName: string, rawSlug?: string): string {
  if (!rawName) return '';

  let name = rawName.trim();
  const slug = (rawSlug || name.toLowerCase().replace(/[^a-z0-9]+/g, '-')).trim();

  // Fix spacing and 'other' patterns
  name = name.replace(/\s*-\s*other\b|\s{2,}other\b/gi, ' (Other)');

  // Top level Shopify taxonomy domains
  const domainMap: [string, string][] = [
    ['marketing-and-conversion', 'Marketing & Conversion'],
    ['orders-and-shipping', 'Orders & Shipping'],
    ['selling-products', 'Selling Products'],
    ['store-design', 'Store Design'],
    ['store-management', 'Store Management'],
    ['finding-products', 'Finding Products'],
    ['sales-channels', 'Sales Channels'],
  ];

  for (const [domainSlug, domainTitle] of domainMap) {
    if (slug.startsWith(`${domainSlug}-`)) {
      const remainder = slug.slice(domainSlug.length + 1);

      // Extract parts and title-case them
      const rawParts = remainder
        .split('-')
        .map((p) => p.trim())
        .filter(Boolean);

      // De-duplicate repetitive words (e.g., 'shipping', 'solutions', 'shipping' -> 'Shipping', 'Solutions')
      const cleanParts: string[] = [];
      const seenWords = new Set<string>();

      // Domain keywords to avoid repeating unnecessarily
      const domainKeywords = domainTitle
        .toLowerCase()
        .replace('&', '')
        .split(/\s+/);

      for (const part of rawParts) {
        const lower = part.toLowerCase();
        // Capitalize SEO, POD, 3PL, etc.
        let formattedPart =
          lower === 'seo'
            ? 'SEO'
            : lower === 'pod'
            ? 'POD'
            : lower === '3pl'
            ? '3PL'
            : lower === 'vr'
            ? 'VR'
            : lower === 'ar'
            ? 'AR'
            : part.charAt(0).toUpperCase() + part.slice(1);

        if (seenWords.has(lower) && (domainKeywords.includes(lower) || cleanParts.length > 0)) {
          continue;
        }
        seenWords.add(lower);
        cleanParts.push(formattedPart);
      }

      const leafTitle = cleanParts.join(' ');
      return leafTitle ? `${leafTitle} (${domainTitle})` : domainTitle;
    }
  }

  // Handle standard title-casing and cleanups
  return name
    .split(' ')
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      if (lower === 'seo') return 'SEO';
      if (lower === '3pl') return '3PL';
      if (lower === 'pod') return 'POD';
      if (lower === 'and') return '&';
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
}

/**
 * Returns consistent pricing model labels across all 6 views.
 * Strictly uses 'Unknown / Unclassified' for unknown types rather than
 * misleadingly labeling them all as 'Custom / Enterprise'.
 */
export function formatPricingType(type?: string | null): {
  label: string;
  badgeClass: string;
  borderClass: string;
  dotColor: string;
} {
  const norm = (type || 'unknown').toLowerCase().trim();

  switch (norm) {
    case 'paid':
      return {
        label: 'Paid',
        badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
        borderClass: 'border-blue-200',
        dotColor: '#3b82f6',
      };
    case 'freemium':
      return {
        label: 'Freemium',
        badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        borderClass: 'border-emerald-200',
        dotColor: '#10b981',
      };
    case 'free':
      return {
        label: 'Free',
        badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
        borderClass: 'border-amber-200',
        dotColor: '#f59e0b',
      };
    case 'unknown':
    default:
      return {
        label: 'Unknown / Unclassified',
        badgeClass: 'bg-slate-100 text-slate-700 border-slate-300',
        borderClass: 'border-slate-300',
        dotColor: '#64748b',
      };
  }
}

/**
 * Deduplicates and selects the most descriptive category tags for an app card
 * to avoid repetitive ancestral breadcrumb tags (e.g. 'Marketing and conversion social trust'
 * alongside 'Marketing and conversion social trust product reviews').
 */
export function deduplicateAppCategories(
  categories?: { id: number; slug: string; name: string }[]
): { id: number; slug: string; name: string; displayName: string }[] {
  if (!categories || categories.length === 0) return [];

  const formatted = categories.map((c) => ({
    ...c,
    displayName: formatCategoryName(c.name, c.slug),
  }));

  // Deduplicate by displayName
  const uniqueMap = new Map<string, (typeof formatted)[0]>();
  for (const item of formatted) {
    if (!uniqueMap.has(item.displayName)) {
      uniqueMap.set(item.displayName, item);
    }
  }

  // Cap at 3 most descriptive tags for compact card display
  return Array.from(uniqueMap.values()).slice(0, 3);
}
