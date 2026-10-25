import React, { useState } from 'react';
import type { CountItem, TimelineItem } from '../types';
import { getClassColor, formatTime } from '../constants';

export const ObjectsByClassChart: React.FC<{ counts: CountItem[] }> = ({ counts }) => {
  const [hovered, setHovered] = useState<string | null>(null);
  if (!counts.length) {
    return <div style={{ color: 'var(--muted)', padding: '24px', textAlign: 'center' }}>No detections</div>;
  }

  const sorted = [...counts].sort((a, b) => b.count - a.count);
  const maxCount = Math.max(...sorted.map((c) => c.count), 1);
  const total = sorted.reduce((sum, c) => sum + c.count, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {sorted.map((item) => {
        const pct = (item.count / maxCount) * 100;
        const share = total > 0 ? ((item.count / total) * 100).toFixed(1) : '0';
        const color = getClassColor(item.class_name);
        const isHover = hovered === item.class_name;

        return (
          <div
            key={item.class_name}
            onMouseEnter={() => setHovered(item.class_name)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: 'grid',
              gridTemplateColumns: '120px 1fr 60px 50px',
              alignItems: 'center',
              gap: '12px',
              padding: '4px 6px',
              borderRadius: '4px',
              background: isHover ? 'var(--panel-2)' : 'transparent',
              transition: 'background 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '1px', backgroundColor: color }} />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-2)', textTransform: 'capitalize' }}>
                {item.class_name}
              </span>
            </div>
            <div style={{ height: '14px', background: 'var(--panel-3)', borderRadius: '2px', overflow: 'hidden' }}>
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  backgroundColor: color,
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
            <div className="mono" style={{ fontSize: '0.85rem', textAlign: 'right', fontWeight: 600 }}>
              {item.count}
            </div>
            <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--muted)', textAlign: 'right' }}>
              {share}%
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const TimelineHistogram: React.FC<{
  timeline: TimelineItem[];
  title?: string;
  tooltipLabel?: string;
}> = ({ timeline, tooltipLabel = 'objects' }) => {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (!timeline.length) {
    return <div style={{ color: 'var(--muted)', padding: '24px', textAlign: 'center' }}>No timeline data</div>;
  }

  // Aggregate counts per bucket start
  const bucketMap = new Map<number, { start: number; end: number; count: number }>();
  for (const item of timeline) {
    const existing = bucketMap.get(item.bucket_start_sec);
    if (existing) {
      existing.count += item.count;
    } else {
      bucketMap.set(item.bucket_start_sec, {
        start: item.bucket_start_sec,
        end: item.bucket_end_sec,
        count: item.count,
      });
    }
  }

  const buckets = Array.from(bucketMap.values()).sort((a, b) => a.start - b.start);
  const maxCount = Math.max(...buckets.map((b) => b.count), 1);

  const height = 140;

  return (
    <div>
      <div
        style={{
          height: `${height}px`,
          display: 'flex',
          alignItems: 'flex-end',
          gap: '4px',
          borderBottom: '1px solid var(--line-2)',
          paddingBottom: '2px',
        }}
      >
        {buckets.map((b, idx) => {
          const barHeight = Math.max((b.count / maxCount) * (height - 20), b.count > 0 ? 4 : 1);
          const isHover = hoverIdx === idx;

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoverIdx(idx)}
              onMouseLeave={() => setHoverIdx(null)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                height: '100%',
                position: 'relative',
                cursor: 'pointer',
              }}
            >
              {isHover && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: `${barHeight + 6}px`,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'var(--bg-2)',
                    border: '1px solid var(--line-3)',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.72rem',
                    whiteSpace: 'nowrap',
                    zIndex: 20,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                  }}
                >
                  <div className="mono" style={{ color: 'var(--text)', fontWeight: 600 }}>
                    {b.count} {tooltipLabel}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: '0.68rem' }}>
                    {formatTime(b.start)} – {formatTime(b.end)}
                  </div>
                </div>
              )}
              <div
                style={{
                  height: `${barHeight}px`,
                  background: isHover ? 'var(--text)' : 'var(--text-2)',
                  borderRadius: '2px 2px 0 0',
                  opacity: b.count === 0 ? 0.15 : 0.85,
                  transition: 'all 0.15s ease',
                }}
              />
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.7rem', color: 'var(--muted)' }}>
        <span>{formatTime(buckets[0]?.start || 0)}</span>
        <span>{formatTime(buckets[Math.floor(buckets.length / 2)]?.start || 0)}</span>
        <span>{formatTime(buckets[buckets.length - 1]?.end || 0)}</span>
      </div>
    </div>
  );
};

export const ClassMixBar: React.FC<{ counts: CountItem[] }> = ({ counts }) => {
  const active = counts.filter((c) => c.count > 0);
  const total = active.reduce((sum, c) => sum + c.count, 0);

  if (!total) {
    return <div style={{ color: 'var(--muted)', padding: '12px' }}>No detections</div>;
  }

  return (
    <div>
      <div style={{ height: '24px', display: 'flex', borderRadius: '4px', overflow: 'hidden', background: 'var(--panel-3)' }}>
        {active.map((item) => {
          const pct = (item.count / total) * 100;
          const color = getClassColor(item.class_name);
          return (
            <div
              key={item.class_name}
              title={`${item.class_name}: ${item.count} (${pct.toFixed(1)}%)`}
              style={{
                width: `${pct}%`,
                height: '100%',
                backgroundColor: color,
                transition: 'width 0.3s ease',
              }}
            />
          );
        })}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginTop: '10px' }}>
        {active.map((item) => {
          const pct = ((item.count / total) * 100).toFixed(1);
          return (
            <div key={item.class_name} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '1px', backgroundColor: getClassColor(item.class_name) }} />
              <span style={{ color: 'var(--text-2)' }}>{item.class_name}</span>
              <span className="mono" style={{ color: 'var(--muted)' }}>{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
