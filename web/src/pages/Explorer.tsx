import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronRight, Video } from 'lucide-react';
import { fetchRuns } from '../api';
import type { RunSummary } from '../types';
import { ClassBadge } from '../components/ClassBadge';

export const Explorer: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'objects' | 'duration'>('newest');

  useEffect(() => {
    fetchRuns()
      .then((data) => setRuns(data))
      .catch((err) => console.error('Failed to load runs:', err))
      .finally(() => setLoading(false));
  }, []);

  // Collect all unique classes across runs
  const allClasses = Array.from(new Set(runs.flatMap((r) => r.classes))).sort();

  // Filter & Sort
  const filteredRuns = runs
    .filter((run) => {
      const q = searchQuery.toLowerCase().trim();
      const matchQuery =
        !q ||
        run.video_name.toLowerCase().includes(q) ||
        run.id.toLowerCase().includes(q) ||
        (run.location && run.location.toLowerCase().includes(q));
      const matchClass = !selectedClass || run.classes.includes(selectedClass);
      return matchQuery && matchClass;
    })
    .sort((a, b) => {
      if (sortBy === 'objects') return b.total_objects - a.total_objects;
      if (sortBy === 'duration') return b.duration_sec - a.duration_sec;
      return b.id.localeCompare(a.id); // newest by timestamp
    });

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '4px' }}>Run Explorer</h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
          Browse, filter, and inspect past drone surveillance mission runs stored in outputs.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel" style={{ padding: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr 1fr', gap: '14px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              className="input"
              style={{ paddingLeft: '32px' }}
              placeholder="Search by video title, run ID, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div>
            <select
              className="select"
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
            >
              <option value="">All Detected Classes</option>
              {allClasses.map((cls) => (
                <option key={cls} value={cls}>
                  {cls}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              className="select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="newest">Sort by: Newest First</option>
              <option value="objects">Sort by: Most Objects</option>
              <option value="duration">Sort by: Longest Duration</option>
            </select>
          </div>
        </div>
      </div>

      {/* Runs List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>Loading runs...</div>
      ) : filteredRuns.length === 0 ? (
        <div className="panel" style={{ textAlign: 'center', padding: '40px', color: 'var(--muted)' }}>
          No runs matched your criteria.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredRuns.map((run) => (
            <div
              key={run.id}
              onClick={() => navigate(`/results?run=${run.id}`)}
              style={{
                background: 'var(--panel)',
                border: '1px solid var(--line)',
                borderRadius: '6px',
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--line-3)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--line)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                  <Video size={16} color="var(--primary)" />
                  <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text)' }}>
                    {run.video_name}
                  </span>
                  {run.location && <span className="badge">{run.location}</span>}
                  <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
                    {run.id}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: 'var(--muted)', marginBottom: '8px' }}>
                  <span>Processed: {run.processed_at}</span>
                  <span>·</span>
                  <span>Duration: {run.duration_sec.toFixed(1)}s</span>
                  <span>·</span>
                  <span style={{ color: 'var(--text-2)' }}>
                    <strong className="mono">{run.total_objects}</strong> unique objects
                  </span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {run.classes.map((cls) => (
                    <ClassBadge key={cls} name={cls} />
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--muted)' }}>
                <span style={{ fontSize: '0.8rem' }}>Inspect</span>
                <ChevronRight size={18} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
