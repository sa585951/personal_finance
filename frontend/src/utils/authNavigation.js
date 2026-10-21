export function safeRedirectPath(value, fallback = '/') {
  if (typeof value !== 'string' || value.length > 2048) return fallback;
  try {
    const decoded = decodeURIComponent(value);
    const hasControl = [...decoded].some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127);
    if (!decoded.startsWith('/') || decoded.startsWith('//') || decoded.includes('\\') || hasControl) return fallback;
    return new URL(value, window.location.origin).origin === window.location.origin ? value : fallback;
  } catch {
    return fallback;
  }
}
