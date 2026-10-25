import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Download,
  Printer,
  Trash2,
  Video,
  CheckCircle,
} from 'lucide-react';
import { fetchRuns, fetchRun, generateBrief, deleteRun, getFileUrl } from '../api';
import type { RunDetail, RunSummary } from '../types';
import { ClassBadge } from '../components/ClassBadge';
import { ObjectsByClassChart, TimelineHistogram, ClassMixBar } from '../components/Charts';
import { formatTime } from '../constants';

export const Results: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [runsList, setRunsList] = useState<RunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState<boolean>(false);
  const [briefPdfUrl, setBriefPdfUrl] = useState<string | null>(null);

  // Load runs list
  useEffect(() => {
    fetchRuns()
      .then((runs) => {
        setRunsList(runs);
        const queryRun = searchParams.get('run');
        if (queryRun && runs.some((r) => r.id === queryRun)) {
          setSelectedRunId(queryRun);
        } else if (runs.length > 0) {
          setSelectedRunId(runs[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        console.error('Failed to fetch runs:', err);
        setLoadError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });
  }, []);

  // Load detail when selectedRunId changes
  useEffect(() => {
    if (!selectedRunId) return;
    setLoading(true);
    setLoadError(null);
    setRunDetail(null);
    setBriefPdfUrl(null);

    fetchRun(selectedRunId)
      .then((detail) => {
        setRunDetail(detail);
        if (detail.has_brief) {
          setBriefPdfUrl(getFileUrl(detail.id, 'brief.pdf'));
        }
        setSearchParams({ run: selectedRunId }, { replace: true });
      })
      .catch((err: unknown) => {
        console.error('Failed to load run detail:', err);
        setLoadError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, [selectedRunId]);

  const handlePrintBrief = async () => {
    if (!runDetail) return;
    setGeneratingPdf(true);
    try {
      const res = await generateBrief(runDetail.id);
      setBriefPdfUrl(res.path);
    } catch (err: any) {
      alert(`Error generating PDF: ${err.message}`);
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleDelete = async () => {
    if (!runDetail) return;
    if (!confirm(`Are you sure you want to delete ${runDetail.id}?`)) return;
    try {
      await deleteRun(runDetail.id);
      const remaining = runsList.filter((r) => r.id !== runDetail.id);
      setRunsList(remaining);
      if (remaining.length > 0) {
        setSelectedRunId(remaining[0].id);
      } else {
        setSelectedRunId('');
        setRunDetail(null);
      }
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    }
  };

  if (!runsList.length && !loading) {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
        <Video size={48} color="var(--muted)" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>No Surveillance Runs Indexed Yet</h2>
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginBottom: '20px' }}>
          Analyze a recorded video to generate detection metrics, track logs, and tactical briefs.
        </p>
        <button className="btn btn-primary" onClick={() => navigate('/analyze')}>
          Start an Analysis Run
        </button>
      </div>
    );
  }

  const totalObjects = runDetail?.counts.reduce((sum, c) => sum + c.count, 0) || 0;
  const mostCommon = runDetail?.counts[0]?.class_name || '—';

  if (loadError) {
    return (
      <div className="panel" role="alert" style={{ textAlign: 'center', padding: '60px 20px' }}>
        <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Unable to load analysis results</h2>
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginBottom: '20px' }}>{loadError}</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Run Switcher & Action Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--muted)', fontWeight: 600 }}>SELECT RUN:</label>
          <select
            className="select mono"
            style={{ width: 'auto', minWidth: '280px', fontWeight: 600 }}
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
          >
            {runsList.map((r) => (
              <option key={r.id} value={r.id}>
                {r.video_name} ({r.id}) — {r.total_objects} objects
              </option>
            ))}
          </select>
        </div>

        {runDetail && (
          <div style={{ display: 'flex', gap: '10px' }}>
            <a
              href={getFileUrl(runDetail.id, 'detections.csv')}
              download="detections.csv"
              className="btn btn-secondary"
            >
              <Download size={15} />
              Download CSV
            </a>

            {briefPdfUrl ? (
              <a href={briefPdfUrl} download="brief.pdf" className="btn btn-primary">
                <CheckCircle size={15} />
                Download Brief PDF
              </a>
            ) : (
              <button
                className="btn btn-secondary"
                disabled={generatingPdf}
                onClick={handlePrintBrief}
              >
                <Printer size={15} />
                {generatingPdf ? 'Generating PDF...' : 'Print Brief'}
              </button>
            )}

            <button className="btn btn-danger" onClick={handleDelete} title="Delete this run">
              <Trash2 size={15} />
            </button>
          </div>
        )}
      </div>

      {loading || !runDetail ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--muted)' }}>
          Loading analysis results...
        </div>
      ) : (
        <>
          {/* Header Title & Date */}
          <div style={{ marginBottom: '20px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '4px' }}>
              Results: {runDetail.video_name}
            </h1>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', gap: '16px' }}>
              <span>
                Run <strong className="mono">{runDetail.id}</strong>
              </span>
              <span>·</span>
              <span>Processed: {runDetail.processed_at}</span>
              {runDetail.location && (
                <>
                  <span>·</span>
                  <span className="badge">{runDetail.location}</span>
                </>
              )}
            </div>
          </div>

          {/* KPI Summary Grid */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">UNIQUE OBJECTS</div>
              <div className="kpi-value">{totalObjects}</div>
              <div className="kpi-sub">Distinct tracked IDs</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">CLASSES DETECTED</div>
              <div className="kpi-value">{runDetail.counts.length}</div>
              <div className="kpi-sub">Target categories</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">MOST COMMON</div>
              <div className="kpi-value" style={{ textTransform: 'capitalize' }}>
                {mostCommon}
              </div>
              <div className="kpi-sub">Primary classification</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">VIDEO DURATION</div>
              <div className="kpi-value">{runDetail.duration_sec.toFixed(1)}s</div>
              <div className="kpi-sub">{formatTime(runDetail.duration_sec)} duration</div>
            </div>
            {runDetail.processing_fps && (
              <div className="kpi-card">
                <div className="kpi-label">PROCESSING SPEED</div>
                <div className="kpi-value">{runDetail.processing_fps} FPS</div>
                <div className="kpi-sub">{runDetail.device || 'CUDA GPU'}</div>
              </div>
            )}
          </div>

          {/* Tactical Summary Callout */}
          <div className="panel" style={{ borderLeft: '4px solid var(--primary)', background: 'var(--panel-2)' }}>
            <div className="panel-title">SUMMARY BRIEF</div>
            <p style={{ fontSize: '0.88rem', color: 'var(--text)', lineHeight: 1.6, marginTop: '6px' }}>
              {runDetail.summary}
            </p>
          </div>

          {/* Primary Charts (2 Column Grid) */}
          <div className="grid-2">
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">UNIQUE OBJECTS BY CLASS</div>
              </div>
              <ObjectsByClassChart counts={runDetail.counts} />
            </div>

            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">NEW OBJECTS FIRST SEEN (5-SECOND BUCKETS)</div>
              </div>
              <TimelineHistogram timeline={runDetail.timeline} tooltipLabel="new objects" />
            </div>
          </div>

          {/* Full Width Active Visibility Timeline */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">OBJECTS VISIBLE OVER TIME (ACTIVE INTERVALS)</div>
            </div>
            <TimelineHistogram timeline={runDetail.visible_timeline} tooltipLabel="active objects" />
          </div>

          {/* Class Mix Stacked Bar */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">CLASS MIX PROPORTION</div>
            </div>
            <ClassMixBar counts={runDetail.counts} />
          </div>

          {/* Annotated Video Player */}
          {runDetail.has_annotated_video && (
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">ANNOTATED VIDEO REPLAY</div>
                <span className="badge">H.264 MP4</span>
              </div>
              <div style={{ maxWidth: '960px', margin: '0 auto', borderRadius: '6px', overflow: 'hidden' }}>
                <video
                  controls
                  style={{ width: '100%', height: 'auto', background: '#000', display: 'block' }}
                  src={getFileUrl(runDetail.id, 'annotated.mp4')}
                >
                  Your browser does not support HTML5 video playback.
                </video>
              </div>
            </div>
          )}

          {/* Object Snapshots Gallery */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">OBJECT CROPPED SNAPSHOTS ({runDetail.snapshots.length})</div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
                Sorted by highest model confidence
              </span>
            </div>

            {runDetail.snapshots.length === 0 ? (
              <div style={{ color: 'var(--muted)', padding: '20px', textAlign: 'center' }}>
                No cropped object snapshots saved for this run.
              </div>
            ) : (
              <div className="snapshots-grid">
                {runDetail.snapshots.map((item) => (
                  <div key={`${item.class_name}_${item.track_id}`} className="snapshot-card">
                    <div className="snapshot-img-wrap">
                      {item.path ? (
                        <img src={getFileUrl(runDetail.id, item.path)} alt={item.class_name} />
                      ) : (
                        <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>Snapshot Unavailable</span>
                      )}
                    </div>
                    <div className="snapshot-body">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <ClassBadge name={item.class_name} />
                        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
                          ID {item.track_id}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
                        <span>Seen: {formatTime(item.first_seen_sec)}</span>
                        <span>Conf: <strong className="mono" style={{ color: 'var(--text-2)' }}>{item.avg_confidence ? `${(item.avg_confidence * 100).toFixed(0)}%` : '—'}</strong></span>
                      </div>
                      <button
                        className="btn btn-secondary"
                        style={{ width: '100%', marginTop: '10px', padding: '4px', fontSize: '0.72rem' }}
                        onClick={() => navigate(`/dossier?run=${runDetail.id}&class=${item.class_name}&track=${item.track_id}`)}
                      >
                        Inspect Dossier
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
