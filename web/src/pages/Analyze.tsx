import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  Play,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { fetchModelInfo, fetchSampleVideos, startDetectionStream } from '../api';
import type { ModelInfo, SampleVideo, DetectSSEEvent } from '../types';
import { getClassColor } from '../constants';

export const Analyze: React.FC = () => {
  const navigate = useNavigate();
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [sampleVideos, setSampleVideos] = useState<SampleVideo[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>('');
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);

  // Detection streaming states
  const [isProcessing, setIsProcessing] = useState(false);
  const [progressData, setProgressData] = useState<{
    processed: number;
    total: number;
    percent: number;
    fps: number;
    elapsed: number;
  } | null>(null);
  const [previewFrame, setPreviewFrame] = useState<string | null>(null);
  const [liveCounts, setLiveCounts] = useState<Record<string, number>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [completedRunId, setCompletedRunId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    fetchModelInfo()
      .then((info) => {
        setModelInfo(info);
        setSelectedClasses(info.default_classes);
      })
      .catch((err) => console.error('Failed to load model info:', err));

    fetchSampleVideos()
      .then((samples) => {
        setSampleVideos(samples);
      })
      .catch((err) => console.error('Failed to load sample videos:', err));

    return () => {
      if (cancelStreamRef.current) cancelStreamRef.current();
    };
  }, []);

  const toggleClass = (className: string) => {
    if (selectedClasses.includes(className)) {
      setSelectedClasses(selectedClasses.filter((c) => c !== className));
    } else {
      setSelectedClasses([...selectedClasses, className]);
    }
  };

  const handleStart = () => {
    if (!selectedFile && !selectedSample) {
      setErrorMsg('Please select a video file or a sample video.');
      return;
    }
    if (!selectedClasses.length) {
      setErrorMsg('Please select at least one object class.');
      return;
    }

    setErrorMsg(null);
    setIsProcessing(true);
    setProgressData({ processed: 0, total: 100, percent: 0, fps: 0, elapsed: 0 });
    setPreviewFrame(null);
    setLiveCounts({});
    setCompletedRunId(null);

    const cancel = startDetectionStream(
      selectedFile,
      selectedSample || null,
      selectedClasses,
      (event: DetectSSEEvent) => {
        if (event.type === 'progress') {
          setProgressData({
            processed: event.processed,
            total: event.total,
            percent: event.percent,
            fps: event.fps,
            elapsed: event.elapsed,
          });
        } else if (event.type === 'preview') {
          setPreviewFrame(event.frame);
          setLiveCounts(event.counts);
        } else if (event.type === 'complete') {
          setIsProcessing(false);
          setCompletedRunId(event.run_id);
        } else if (event.type === 'error') {
          setIsProcessing(false);
          setErrorMsg(event.message);
        }
      },
      (err) => {
        setIsProcessing(false);
        setErrorMsg(err.message || 'Stream connection error');
      }
    );

    cancelStreamRef.current = cancel;
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '4px' }}>
          Analyze Surveillance Video
        </h1>
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
          Upload recorded drone footage or choose a preloaded clip. Tracking runs on CUDA using YOLO11s and ByteTrack.
        </p>
      </div>

      {errorMsg && (
        <div
          style={{
            background: 'rgba(224, 82, 82, 0.1)',
            border: '1px solid var(--crit)',
            borderRadius: '6px',
            padding: '12px 16px',
            color: 'var(--crit)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '20px',
            fontSize: '0.85rem',
          }}
        >
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {completedRunId && (
        <div
          style={{
            background: 'rgba(63, 178, 107, 0.1)',
            border: '1px solid var(--ok)',
            borderRadius: '6px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <CheckCircle2 color="var(--ok)" size={24} />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text)' }}>Detection Run Complete!</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                Processed run indexed as <span className="mono">{completedRunId}</span>
              </div>
            </div>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => navigate(`/results?run=${completedRunId}`)}
          >
            Open Results
          </button>
        </div>
      )}

      {isProcessing ? (
        /* Real-Time Processing View */
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">LIVE DETECTION IN PROGRESS</div>
            <div className="badge mono" style={{ background: 'var(--primary)', color: '#fff' }}>
              ACTIVE PIPELINE
            </div>
          </div>

          {/* Progress bar */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-2)' }}>
              <span>
                Processing Frame <strong className="mono">{progressData?.processed.toLocaleString() || 0}</strong> of{' '}
                <span className="mono">{progressData?.total.toLocaleString() || '...'}</span>
              </span>
              <span className="mono" style={{ fontWeight: 600 }}>
                {progressData?.percent.toFixed(1) || 0}%
              </span>
            </div>
            <div className="progress-bar-wrap">
              <div className="progress-bar-fill" style={{ width: `${progressData?.percent || 0}%` }} />
            </div>
            <div style={{ display: 'flex', gap: '18px', fontSize: '0.75rem', color: 'var(--muted)' }}>
              <span>
                Speed: <strong className="mono" style={{ color: 'var(--text)' }}>{progressData?.fps || 0} FPS</strong>
              </span>
              <span>
                Elapsed: <strong className="mono" style={{ color: 'var(--text)' }}>{progressData?.elapsed || 0}s</strong>
              </span>
            </div>
          </div>

          {/* Live Preview & Live Counts Grid */}
          <div className="grid-2">
            <div style={{ background: 'var(--bg-2)', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--line-2)' }}>
              <div style={{ padding: '8px 12px', background: 'var(--panel-2)', fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600 }}>
                LIVE ANNOTATED FRAME PREVIEW
              </div>
              <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {previewFrame ? (
                  <img src={previewFrame} alt="Live preview" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                ) : (
                  <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>Waiting for preview frames...</div>
                )}
              </div>
            </div>

            <div style={{ background: 'var(--bg-2)', borderRadius: '6px', padding: '16px', border: '1px solid var(--line-2)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '12px' }}>
                LIVE TRACK COUNTS (MIN LENGTH APPLIED)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedClasses.map((cls) => {
                  const count = liveCounts[cls] || 0;
                  const color = getClassColor(cls);
                  return (
                    <div
                      key={cls}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 12px',
                        background: 'var(--panel-2)',
                        borderRadius: '4px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '1px', backgroundColor: color }} />
                        <span style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>{cls}</span>
                      </div>
                      <span className="mono" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                        {count}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Configuration View */
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '24px' }}>
          {/* Left Column: Video & Classes */}
          <div>
            {/* File Upload / Sample Selector */}
            <div className="panel">
              <div className="panel-title">1. SOURCE VIDEO</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' }}>
                {/* Upload Zone */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    border: '1px dashed var(--line-3)',
                    borderRadius: '6px',
                    padding: '24px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: selectedFile ? 'var(--panel-2)' : 'var(--bg-2)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    accept=".mp4,.avi,.mov"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        setSelectedFile(e.target.files[0]);
                        setSelectedSample('');
                      }
                    }}
                  />
                  <Upload size={28} color="var(--muted)" style={{ margin: '0 auto 8px' }} />
                  <div style={{ fontSize: '0.9rem', color: 'var(--text)', fontWeight: 500 }}>
                    {selectedFile ? selectedFile.name : 'Click or drop video clip here'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '4px' }}>
                    Supported formats: MP4, AVI, MOV
                  </div>
                </div>

                {/* Preloaded Samples Dropdown */}
                {sampleVideos.length > 0 && (
                  <div>
                    <label style={{ fontSize: '0.75rem', color: 'var(--muted)', display: 'block', marginBottom: '6px' }}>
                      Or select from preloaded test clips:
                    </label>
                    <select
                      className="select"
                      value={selectedSample}
                      onChange={(e) => {
                        setSelectedSample(e.target.value);
                        if (e.target.value) setSelectedFile(null);
                      }}
                    >
                      <option value="">-- Choose a test video --</option>
                      {sampleVideos.map((s) => (
                        <option key={s.path} value={s.path}>
                          {s.name} ({s.size_mb} MB)
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* Target Class Selection */}
            <div className="panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div className="panel-title">2. TARGET OBJECT CLASSES</div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                    onClick={() => setSelectedClasses(modelInfo?.all_classes || [])}
                  >
                    All
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                    onClick={() => setSelectedClasses(modelInfo?.default_classes || [])}
                  >
                    Reset Defaults
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {modelInfo?.all_classes.map((cls) => {
                  const isSelected = selectedClasses.includes(cls);
                  const color = getClassColor(cls);
                  return (
                    <button
                      key={cls}
                      onClick={() => toggleClass(cls)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        background: isSelected ? 'var(--panel-3)' : 'var(--panel-2)',
                        border: isSelected ? '1px solid var(--text)' : '1px solid var(--line-2)',
                        color: isSelected ? 'var(--text)' : 'var(--muted)',
                        transition: 'all 0.1s ease',
                      }}
                    >
                      <span
                        style={{
                          width: '7px',
                          height: '7px',
                          borderRadius: '1px',
                          backgroundColor: isSelected ? color : 'var(--muted)',
                        }}
                      />
                      <span style={{ textTransform: 'capitalize' }}>{cls}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              className="btn btn-primary"
              style={{ width: '100%', padding: '14px', fontSize: '1rem', fontWeight: 600 }}
              disabled={(!selectedFile && !selectedSample) || !selectedClasses.length}
              onClick={handleStart}
            >
              <Play size={18} />
              Start Surveillance Analysis
            </button>
          </div>

          {/* Right Column: Parameters & Info */}
          <div>
            <div className="panel">
              <div className="panel-title">PIPELINE CONFIGURATION</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>YOLO Model</span>
                  <span className="mono" style={{ fontSize: '0.8rem' }}>{modelInfo?.model_name || 'yolo11s.pt'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Confidence Threshold</span>
                  <span className="mono" style={{ fontSize: '0.8rem' }}>{modelInfo?.confidence_threshold || 0.35}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Inference Image Size</span>
                  <span className="mono" style={{ fontSize: '0.8rem' }}>{modelInfo?.image_size || 960}px</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Min Track Length</span>
                  <span className="mono" style={{ fontSize: '0.8rem' }}>{modelInfo?.min_track_frames || 5} frames</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Compute Device</span>
                  <span className="badge" style={{ color: modelInfo?.cuda_available ? 'var(--ok)' : 'var(--warn)' }}>
                    {modelInfo?.cuda_available ? `CUDA (${modelInfo.device_name || 'GPU'})` : 'CPU'}
                  </span>
                </div>
              </div>
            </div>

            <div className="panel" style={{ background: 'var(--panel-2)' }}>
              <div className="panel-title">TACTICAL NOTE</div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-2)', lineHeight: 1.6, marginTop: '8px' }}>
                Only tracks meeting or exceeding the minimum length (5 frames) are logged to <span className="mono">detections.csv</span> and included in tactical briefs. Real-time preview frames are downscaled for low-latency browser streaming.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
