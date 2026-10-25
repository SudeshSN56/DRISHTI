import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Crosshair } from 'lucide-react';
import { fetchRun, fetchRuns, getFileUrl } from '../api';
import type { RunDetail, SnapshotItem } from '../types';
import { ClassBadge } from '../components/ClassBadge';
import { formatTime, getClassColor } from '../constants';

export const Dossier: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentIdx, setCurrentIdx] = useState<number>(0);

  const runId = searchParams.get('run');
  const targetClass = searchParams.get('class');
  const targetTrack = searchParams.get('track');

  useEffect(() => {
    if (runId) {
      loadRun(runId);
    } else {
      // Pick first run if no run query param
      fetchRuns()
        .then((runs) => {
          if (runs.length > 0) {
            loadRun(runs[0].id);
          } else {
            setLoading(false);
          }
        })
        .catch(() => setLoading(false));
    }
  }, [runId]);

  const loadRun = (id: string) => {
    setLoading(true);
    fetchRun(id)
      .then((detail) => {
        setRunDetail(detail);
        if (targetClass && targetTrack) {
          const found = detail.snapshots.findIndex(
            (s) => s.class_name === targetClass && s.track_id === targetTrack
          );
          if (found !== -1) {
            setCurrentIdx(found);
            return;
          }
        }
        setCurrentIdx(0);
      })
      .catch((err) => console.error('Failed to load dossier:', err))
      .finally(() => setLoading(false));
  };

  const snapshots = runDetail?.snapshots || [];
  const currentObject: SnapshotItem | undefined = snapshots[currentIdx];

  const handleSelectObject = (idx: number) => {
    setCurrentIdx(idx);
    const obj = snapshots[idx];
    if (obj && runDetail) {
      setSearchParams({ run: runDetail.id, class: obj.class_name, track: obj.track_id });
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '60px', color: 'var(--muted)' }}>Loading Dossier...</div>;
  }

  if (!runDetail || !snapshots.length) {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
        <Crosshair size={44} color="var(--muted)" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>No Tracked Object Selected</h2>
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginBottom: '20px' }}>
          Select an object snapshot from the Results page to view its full surveillance dossier.
        </p>
        <button className="btn btn-primary" onClick={() => navigate('/results')}>
          Go to Results
        </button>
      </div>
    );
  }

  const durationVisible = currentObject.last_seen_sec - currentObject.first_seen_sec;
  const sameClassObjects = snapshots.filter(
    (s) => s.class_name === currentObject.class_name && s.track_id !== currentObject.track_id
  );

  return (
    <div>
      {/* Top back button & title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <button
          className="btn btn-secondary"
          onClick={() => navigate(`/results?run=${runDetail.id}`)}
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <ArrowLeft size={16} />
          Back to Results
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
            Object <strong className="mono">{currentIdx + 1}</strong> of <span className="mono">{snapshots.length}</span>
          </span>
          <button
            className="btn btn-secondary"
            disabled={currentIdx === 0}
            onClick={() => handleSelectObject(currentIdx - 1)}
            style={{ padding: '6px 10px' }}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            className="btn btn-secondary"
            disabled={currentIdx >= snapshots.length - 1}
            onClick={() => handleSelectObject(currentIdx + 1)}
            style={{ padding: '6px 10px' }}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* Main Dossier Split */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', marginBottom: '24px' }}>
        {/* Left: Snapshot Image Display */}
        <div className="panel" style={{ padding: '16px' }}>
          <div className="panel-title">CROPPED TARGET SNAPSHOT</div>
          <div
            style={{
              height: '380px',
              background: 'var(--bg-2)',
              borderRadius: '6px',
              border: `2px solid ${getClassColor(currentObject.class_name)}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              marginTop: '12px',
            }}
          >
            {currentObject.path ? (
              <img
                src={getFileUrl(runDetail.id, currentObject.path)}
                alt={currentObject.class_name}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Snapshot Unavailable</div>
            )}
          </div>
        </div>

        {/* Right: Target Intel Table */}
        <div className="panel">
          <div className="panel-title">TARGET DOSSIER & TELEMETRY</div>

          <div style={{ margin: '16px 0 24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ClassBadge name={currentObject.class_name} />
            <span className="mono" style={{ fontSize: '1.2rem', fontWeight: 700 }}>
              TRACK ID #{currentObject.track_id}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>First Seen</span>
              <span className="mono" style={{ fontSize: '0.85rem' }}>{formatTime(currentObject.first_seen_sec)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Last Seen</span>
              <span className="mono" style={{ fontSize: '0.85rem' }}>{formatTime(currentObject.last_seen_sec)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Active Duration</span>
              <span className="mono" style={{ fontSize: '0.85rem' }}>{durationVisible.toFixed(2)} seconds</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Average Confidence</span>
              <span className="mono" style={{ fontSize: '0.85rem', color: 'var(--ok)', fontWeight: 600 }}>
                {currentObject.avg_confidence ? `${(currentObject.avg_confidence * 100).toFixed(1)}%` : '—'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Source Run</span>
              <span className="mono" style={{ fontSize: '0.85rem' }}>{runDetail.id}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>Source Video</span>
              <span style={{ fontSize: '0.85rem' }}>{runDetail.video_name}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Other Objects of same class */}
      {sameClassObjects.length > 0 && (
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              OTHER {currentObject.class_name.toUpperCase()} OBJECTS IN THIS RUN ({sameClassObjects.length})
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
            {sameClassObjects.slice(0, 10).map((obj) => {
              const objIdx = snapshots.indexOf(obj);
              return (
                <div
                  key={obj.track_id}
                  onClick={() => handleSelectObject(objIdx)}
                  style={{
                    minWidth: '120px',
                    width: '120px',
                    background: 'var(--bg-2)',
                    border: '1px solid var(--line-2)',
                    borderRadius: '4px',
                    padding: '8px',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.1s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--line-3)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--line-2)')}
                >
                  <div style={{ height: '70px', background: 'var(--panel)', marginBottom: '6px', borderRadius: '2px', overflow: 'hidden' }}>
                    {obj.path ? (
                      <img src={getFileUrl(runDetail.id, obj.path)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <div style={{ color: 'var(--muted)', fontSize: '0.65rem', paddingTop: '24px' }}>No image</div>
                    )}
                  </div>
                  <div className="mono" style={{ fontSize: '0.75rem', fontWeight: 600 }}>
                    #{obj.track_id}
                  </div>
                  <div className="mono" style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>
                    {formatTime(obj.first_seen_sec)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
