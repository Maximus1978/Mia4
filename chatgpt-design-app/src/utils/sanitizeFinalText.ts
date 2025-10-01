const FUSED_PREFIX_PATTERN = /^(?:\s*(?:assistant\s*final|assistantfinal)[\s:,-]*){1,3}/i;

export function sanitizeFinalText(input: string): string {
  if (!input) {
    return input;
  }
  const before = input;
  const stripped = before.replace(FUSED_PREFIX_PATTERN, '').trimStart();
  return stripped;
}

export default sanitizeFinalText;
