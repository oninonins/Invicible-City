/**
 * Centralized API base URL.
 * Single source of truth — replaces the duplicated inline fallback in every component.
 *
 * NEXT_PUBLIC_API_URL is inlined by the Next.js compiler at build time.
 * The fallback ensures the dev server works without an .env file.
 */
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL as string) ?? "http://localhost:8000/api/v1";
