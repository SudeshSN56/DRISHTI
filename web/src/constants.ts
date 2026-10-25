export const CLASS_COLORS: Record<string, string> = {
  person: '#fab219',
  car: '#6b9bea',
  truck: '#ec835a',
  bus: '#d03b3b',
  bicycle: '#3fb26b',
  motorcycle: '#b07be0',
  boat: '#4cc3d9',
  bird: '#c8d96b',
  dog: '#e08fb4',
  cat: '#e0b48f',
  horse: '#8f9be0',
  cow: '#9bc48f',
  sheep: '#c4c4c4',
};

export function getClassColor(className: string): string {
  const lower = className.toLowerCase();
  if (CLASS_COLORS[lower]) {
    return CLASS_COLORS[lower];
  }
  // Deterministic fallback
  let hash = 0;
  for (let i = 0; i < lower.length; i++) {
    hash = lower.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 58%, 62%)`;
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs < 10 ? '0' : ''}${secs.toFixed(1)}`;
}
