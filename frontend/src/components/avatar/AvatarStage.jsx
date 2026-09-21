/**
 * AvatarStage - OWNER: Member 1 (AI Avatar Tutor & Intelligent Learning).
 * See plan.md §6.6, §6.7.
 *
 * Tier A: An interactive, animated SVG tutor avatar featuring:
 * - Real-time mouth lipsync driven by the viseme timeline
 * - Expression state machine (neutral, thinking, explaining, encouraging)
 * - Natural eye blinking every 3-6 seconds
 * - Idle breathing and subtle head motion
 * - Web Speech API synthesis for spoken speech playback
 *
 * Tier B: Seamlessly renders SyncTalk video stream when present.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX, Sparkles, Activity, MessageSquare } from 'lucide-react';

// Used when a message is replayed without a timeline (handleSpeakMessage sends
// text but no visemes). Stepped at a syllable-ish rate rather than per frame.
const FALLBACK_CYCLE = ['AA', 'E', 'O', 'I', 'U', 'M'];
const FALLBACK_STEPS_PER_SEC = 11;

/**
 * Viseme showing at `elapsed` seconds.
 *
 * Scans backwards in place: the previous `[...visemes].reverse().find(...)`
 * copied and reversed the whole timeline on every animation frame, and a
 * typical 66-word reply is ~243 entries.
 */
function visemeAt(visemes, elapsed) {
  if (!visemes || visemes.length === 0) {
    const step = Math.floor(elapsed * FALLBACK_STEPS_PER_SEC);
    return FALLBACK_CYCLE[step % FALLBACK_CYCLE.length];
  }
  for (let i = visemes.length - 1; i >= 0; i -= 1) {
    if (visemes[i].t <= elapsed) return visemes[i].v;
  }
  return 'sil';
}

export default function AvatarStage({
  expression = 'neutral',
  visemes = [],
  spokenText = '',
  isSpeaking = false,
  onSpeechEnd = null,
  videoStreamUrl = null,
  audioMuted = false,
  onToggleMute = null,
}) {
  const [activeViseme, setActiveViseme] = useState('sil');
  const [isBlinking, setIsBlinking] = useState(false);
  const [currentExpression, setCurrentExpression] = useState(expression);
  const synthUtteranceRef = useRef(null);
  // Held in a ref so the speech effect does not tear down (and cancel speech
  // mid-sentence) every time the parent re-renders with a new callback.
  const onSpeechEndRef = useRef(onSpeechEnd);
  useEffect(() => {
    onSpeechEndRef.current = onSpeechEnd;
  }, [onSpeechEnd]);

  // Sync expression prop
  useEffect(() => {
    setCurrentExpression(expression);
  }, [expression]);

  // Periodic natural eye blink (every 3.5 to 5.5s)
  useEffect(() => {
    let blinkTimeout;
    const triggerBlink = () => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 160);
      const nextInterval = 3200 + Math.random() * 2500;
      blinkTimeout = setTimeout(triggerBlink, nextInterval);
    };

    blinkTimeout = setTimeout(triggerBlink, 3000);
    return () => clearTimeout(blinkTimeout);
  }, []);

  // Browser Web Speech API (speechSynthesis) integration + viseme animation
  useEffect(() => {
    if (!spokenText || typeof window === 'undefined' || !window.speechSynthesis) {
      return undefined;
    }

    if (audioMuted) {
      window.speechSynthesis.cancel();
      // Drive visemes on a simulated timer if muted
      if (isSpeaking && visemes.length > 0) {
        const startTime = Date.now();
        const duration = (visemes[visemes.length - 1]?.t || 2.0) * 1000;
        let shownViseme = null;
        const interval = setInterval(() => {
          const elapsed = (Date.now() - startTime) / 1000;
          const next = visemeAt(visemes, elapsed);
          if (next !== shownViseme) {
            shownViseme = next;
            setActiveViseme(next);
          }
          if (elapsed * 1000 >= duration + 200) {
            clearInterval(interval);
            setActiveViseme('sil');
            onSpeechEndRef.current?.();
          }
        }, 50);
        return () => clearInterval(interval);
      }
      return undefined;
    }

    if (isSpeaking && spokenText) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(spokenText);
      synthUtteranceRef.current = utterance;
      utterance.rate = 1.02;
      utterance.pitch = 1.05;

      // Select a natural English voice if available
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(
        (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny'))
      ) || voices.find((v) => v.lang.startsWith('en'));
      if (preferredVoice) utterance.voice = preferredVoice;

      const startTime = performance.now();

      let animId;
      let shownViseme = null;
      const step = () => {
        const elapsed = (performance.now() - startTime) / 1000;
        const next = visemeAt(visemes, elapsed);
        // Only touch state when the mouth shape actually changes. Calling
        // setActiveViseme every frame re-rendered the whole SVG 60x a second.
        if (next !== shownViseme) {
          shownViseme = next;
          setActiveViseme(next);
        }
        animId = requestAnimationFrame(step);
      };
      animId = requestAnimationFrame(step);

      utterance.onend = () => {
        cancelAnimationFrame(animId);
        setActiveViseme('sil');
        onSpeechEndRef.current?.();
      };

      utterance.onerror = () => {
        cancelAnimationFrame(animId);
        setActiveViseme('sil');
        onSpeechEndRef.current?.();
      };

      window.speechSynthesis.speak(utterance);

      return () => {
        cancelAnimationFrame(animId);
        window.speechSynthesis.cancel();
      };
    } else {
      window.speechSynthesis.cancel();
      setActiveViseme('sil');
    }
  }, [spokenText, isSpeaking, audioMuted, visemes]);

  // Expression styling and colors
  const expressionBadges = {
    neutral: { label: 'Listening', bg: 'bg-info-bg text-info-fg border-info/30' },
    thinking: { label: 'Thinking...', bg: 'bg-medium-bg text-medium-fg border-medium/40' },
    explaining: { label: 'Explaining', bg: 'bg-primary-100 text-primary-900 border-primary-300' },
    encouraging: { label: 'Encouraging', bg: 'bg-primary-50 text-primary-700 border-primary-600/40' },
  };

  const currentBadge = expressionBadges[currentExpression] || expressionBadges.neutral;

  // Tier B rendering if SyncTalk is running
  if (videoStreamUrl) {
    return (
      <div className="relative aspect-square w-full overflow-hidden rounded-lg border border-slate-200 bg-slate-950 shadow-xl dark:border-slate-800">
        <img
          src={videoStreamUrl}
          alt="AI Tutor (SyncTalk Live)"
          className="h-full w-full object-cover"
        />
        <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur-md">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          SyncTalk 2D Avatar (GPU)
        </div>
      </div>
    );
  }

  // Mouth SVG paths for all 10 visemes
  const getMouthPath = (v) => {
    switch (v) {
      case 'AA': // Wide open
        return (
          <g>
            <path d="M 82 132 Q 100 118 118 132 Q 100 158 82 132 Z" fill="#4a1525" stroke="#7a2238" strokeWidth="2" />
            <path d="M 90 144 Q 100 140 110 144 Q 100 152 90 144 Z" fill="#e0627c" />
            <path d="M 88 126 Q 100 128 112 126" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
          </g>
        );
      case 'E': // Smiling wide open
        return (
          <g>
            <path d="M 78 132 Q 100 122 122 132 Q 100 150 78 132 Z" fill="#5c1d2e" stroke="#7a2238" strokeWidth="2" />
            <rect x="85" y="128" width="30" height="4" rx="2" fill="#ffffff" />
            <path d="M 88 140 Q 100 136 112 140" fill="#e0627c" />
          </g>
        );
      case 'I': // Slight open slit with teeth
        return (
          <g>
            <path d="M 80 134 Q 100 127 120 134 Q 100 144 80 134 Z" fill="#4a1525" stroke="#7a2238" strokeWidth="1.8" />
            <rect x="86" y="131" width="28" height="3" rx="1.5" fill="#ffffff" />
          </g>
        );
      case 'O': // Round open
        return (
          <g>
            <ellipse cx="100" cy="136" rx="12" ry="14" fill="#4a1525" stroke="#7a2238" strokeWidth="2" />
            <ellipse cx="100" cy="142" rx="7" ry="5" fill="#e0627c" />
          </g>
        );
      case 'U': // Tight small pucker
        return (
          <g>
            <ellipse cx="100" cy="136" rx="8" ry="9" fill="#4a1525" stroke="#7a2238" strokeWidth="2" />
            <circle cx="100" cy="136" r="4" fill="#310d19" />
          </g>
        );
      case 'M': // Closed pressed lips
        return <path d="M 82 136 Q 100 135 118 136" stroke="#993853" strokeWidth="3" strokeLinecap="round" />;
      case 'F': // Upper teeth on lower lip
        return (
          <g>
            <path d="M 82 135 Q 100 133 118 135" stroke="#993853" strokeWidth="3" strokeLinecap="round" />
            <rect x="88" y="131" width="24" height="4" rx="1" fill="#ffffff" />
          </g>
        );
      case 'L': // Open with tongue up
        return (
          <g>
            <path d="M 82 133 Q 100 122 118 133 Q 100 152 82 133 Z" fill="#4a1525" stroke="#7a2238" strokeWidth="2" />
            <ellipse cx="100" cy="131" rx="8" ry="6" fill="#e0627c" />
          </g>
        );
      case 'S': // Clenched teeth smiling
        return (
          <g>
            <path d="M 80 134 Q 100 128 120 134 Q 100 144 80 134 Z" fill="#4a1525" stroke="#7a2238" strokeWidth="1.5" />
            <rect x="85" y="130" width="30" height="6" rx="2" fill="#ffffff" stroke="#cbd5e1" strokeWidth="0.8" />
          </g>
        );
      case 'sil':
      default: // Closed neutral relaxed smile
        return <path d="M 84 135 Q 100 139 116 135" stroke="#a03d58" strokeWidth="2.5" strokeLinecap="round" fill="none" />;
    }
  };

  // Eyebrow tilts based on expression
  const getEyebrowTransforms = () => {
    if (currentExpression === 'thinking') {
      return { left: 'translate(0, -3) rotate(-6 75 75)', right: 'translate(0, -6) rotate(8 125 75)' };
    }
    if (currentExpression === 'encouraging') {
      return { left: 'translate(0, -2) rotate(4 75 75)', right: 'translate(0, -2) rotate(-4 125 75)' };
    }
    if (currentExpression === 'explaining') {
      return { left: 'translate(0, -4)', right: 'translate(0, -4)' };
    }
    return { left: '', right: '' };
  };

  const eyebrows = getEyebrowTransforms();

  return (
    <div className="relative flex aspect-square w-full flex-col items-center justify-center overflow-hidden rounded-lg border-2 border-line bg-primary-50 p-4 dark:border-[#242B35] dark:bg-[#1C222B]">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -top-16 -left-16 h-56 w-56 rounded-full bg-primary-200/40 blur-3xl dark:bg-primary-900/20" />
      <div className="pointer-events-none absolute -bottom-16 -right-16 h-56 w-56 rounded-full bg-info/10 blur-3xl dark:bg-info/10" />

      {/* Top Header Bar */}
      <div className="absolute top-4 inset-x-4 flex items-center justify-between z-10">
        <div className={`flex items-center gap-1.5 rounded-pill border-2 px-3 py-1 text-xs font-semibold uppercase tracking-wide ${currentBadge.bg}`}>
          {currentExpression === 'thinking' && <Sparkles className="h-3.5 w-3.5 animate-spin text-amber-500" />}
          {currentExpression === 'explaining' && <Activity className="h-3.5 w-3.5 animate-pulse text-emerald-500" />}
          {currentExpression === 'encouraging' && <Sparkles className="h-3.5 w-3.5 text-purple-500" />}
          {currentExpression === 'neutral' && <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />}
          <span>{currentBadge.label}</span>
        </div>

        {/* Audio Mute / Speech Toggle */}
        <button
          type="button"
          onClick={onToggleMute}
          title={audioMuted ? 'Unmute voice' : 'Mute voice'}
          className="flex h-9 w-9 items-center justify-center rounded-xl border-2 border-line bg-surface text-muted transition-colors hover:border-line-strong dark:border-[#242B35] dark:bg-[#171C23] dark:text-[#8A94A2]"
        >
          {audioMuted ? <VolumeX className="h-4 w-4 text-hard" /> : <Volume2 className="h-4 w-4 text-primary-600" />}
        </button>
      </div>

      {/* SVG Interactive Avatar */}
      <div className="relative flex h-full w-full items-center justify-center pt-6">
        <svg
          viewBox="0 0 200 200"
          className="h-full w-full max-h-[300px] max-w-[300px] transition-transform duration-500 hover:scale-[1.02]"
        >
          <defs>
            {/* Skin Gradient */}
            <radialGradient id="skinGradient" cx="50%" cy="45%" r="55%">
              <stop offset="0%" stopColor="#ffdfd2" />
              <stop offset="85%" stopColor="#f7c8b8" />
              <stop offset="100%" stopColor="#eab4a2" />
            </radialGradient>

            {/* Hair / Headband Gradient */}
            <linearGradient id="hairGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#4338ca" />
              <stop offset="100%" stopColor="#6366f1" />
            </linearGradient>

            {/* Soft Shadow */}
            <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
              <feDropShadow dx="0" dy="4" stdDeviation="4" floodOpacity="0.15" />
            </filter>
          </defs>

          {/* Body & Shoulders */}
          <g className="transition-transform duration-1000 ease-in-out">
            <path
              d="M 50 200 C 50 165 75 160 100 160 C 125 160 150 165 150 200 Z"
              fill="url(#hairGradient)"
              opacity="0.95"
            />
            {/* Collar */}
            <path d="M 86 160 Q 100 174 114 160" fill="#ffffff" opacity="0.9" />
          </g>

          {/* Neck */}
          <rect x="91" y="140" width="18" height="22" rx="4" fill="#eab4a2" />

          {/* Ears */}
          <circle cx="58" cy="104" r="9" fill="#f7c8b8" />
          <circle cx="58" cy="104" r="5" fill="#eab4a2" opacity="0.6" />
          <circle cx="142" cy="104" r="9" fill="#f7c8b8" />
          <circle cx="142" cy="104" r="5" fill="#eab4a2" opacity="0.6" />

          {/* Head Base */}
          <ellipse
            cx="100"
            cy="102"
            rx="42"
            ry="48"
            fill="url(#skinGradient)"
            filter="url(#softShadow)"
          />

          {/* Stylized Modern Hair (top & sides) */}
          <path
            d="M 58 92 C 54 60 75 48 100 48 C 125 48 146 60 142 92 C 136 70 124 64 100 64 C 76 64 64 70 58 92 Z"
            fill="url(#hairGradient)"
          />

          {/* Eyebrows */}
          <g>
            <path
              d="M 68 76 Q 78 72 88 77"
              stroke="#312e81"
              strokeWidth="3.2"
              strokeLinecap="round"
              fill="none"
              transform={eyebrows.left}
            />
            <path
              d="M 112 77 Q 122 72 132 76"
              stroke="#312e81"
              strokeWidth="3.2"
              strokeLinecap="round"
              fill="none"
              transform={eyebrows.right}
            />
          </g>

          {/* Eyes (Open or Blinking) */}
          <g>
            {isBlinking ? (
              // Blinking Eyes (Curved Lines)
              <>
                <path d="M 72 94 Q 79 99 86 94" stroke="#1e1b4b" strokeWidth="2.8" strokeLinecap="round" fill="none" />
                <path d="M 114 94 Q 121 99 128 94" stroke="#1e1b4b" strokeWidth="2.8" strokeLinecap="round" fill="none" />
              </>
            ) : (
              // Open Intelligent Eyes
              <>
                {/* Left Eye */}
                <ellipse cx="79" cy="93" rx="7" ry="8" fill="#ffffff" />
                <circle cx="80" cy="93" r="5" fill="#1e1b4b" />
                <circle cx="82" cy="91" r="1.8" fill="#ffffff" />
                <circle cx="78" cy="95" r="0.8" fill="#ffffff" />

                {/* Right Eye */}
                <ellipse cx="121" cy="93" rx="7" ry="8" fill="#ffffff" />
                <circle cx="120" cy="93" r="5" fill="#1e1b4b" />
                <circle cx="122" cy="91" r="1.8" fill="#ffffff" />
                <circle cx="118" cy="95" r="0.8" fill="#ffffff" />
              </>
            )}
          </g>

          {/* Soft Cheeks / Blush */}
          <circle cx="68" cy="112" r="6.5" fill="#f43f5e" opacity="0.18" />
          <circle cx="132" cy="112" r="6.5" fill="#f43f5e" opacity="0.18" />

          {/* Nose */}
          <path d="M 98 108 Q 100 114 103 114" stroke="#d99988" strokeWidth="2" strokeLinecap="round" fill="none" />

          {/* Dynamic Animated Mouth (driven by active viseme) */}
          <g className="transition-all duration-75">
            {getMouthPath(activeViseme)}
          </g>
        </svg>
      </div>

      {/* Bottom Subtitle / Live Speaking Indicator */}
      <div className="mt-2 flex w-full flex-col items-center justify-center text-center">
        {isSpeaking ? (
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-400">
            <span className="flex gap-0.5">
              <span className="h-2 w-0.5 animate-bounce bg-primary-600" style={{ animationDelay: '0ms' }} />
              <span className="h-3 w-0.5 animate-bounce bg-primary-600" style={{ animationDelay: '150ms' }} />
              <span className="h-2 w-0.5 animate-bounce bg-primary-600" style={{ animationDelay: '300ms' }} />
            </span>
            <span>Speaking...</span>
            <span className="rounded-md bg-primary-100 px-1.5 font-mono text-[10px] text-primary-900">
              {activeViseme}
            </span>
          </div>
        ) : (
          <p className="flex items-center gap-1.5 text-xs font-bold text-muted dark:text-[#8A94A2]">
            <MessageSquare className="h-3.5 w-3.5" />
            Ready to teach & answer questions
          </p>
        )}
      </div>
    </div>
  );
}
