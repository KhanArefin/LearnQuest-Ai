/**
 * TutorPage - OWNER: Member 1 (AI Avatar Tutor & Intelligent Learning).
 * See plan.md §6.6, §6.7.
 *
 * Full-featured interactive AI Tutor dashboard:
 * - Real-time animated Tier A avatar with lipsync and expression state machine
 * - Socratic conversation chat with markdown and code highlighting
 * - Conversation management (create, list, switch, delete)
 * - Dynamic lesson context attachment (when navigated from a lesson)
 * - Text-to-speech audio narration controls and mute toggles
 * - Responsive desktop split view and mobile-optimized layouts
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  MessageSquare,
  Plus,
  Trash2,
  Volume2,
  VolumeX,
  Sparkles,
  Layers,
  History,
  Info,
  ChevronLeft,
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import AvatarStage from '../../components/avatar/AvatarStage';
import ChatPanel from '../../components/tutor/ChatPanel';
import PageHeader from '../../components/layout/PageHeader';
import { Button, Badge, Spinner } from '../../components/ui';
import {
  listConversations,
  deleteConversation,
  createConversation,
} from '../../api/tutor';
import { getLesson } from '../../api/lessons';

export default function TutorPage() {
  const { conversationId: routeConvId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const lessonId = searchParams.get('lessonId') || searchParams.get('lesson_id');
  const [lessonData, setLessonData] = useState(null);

  // Conversations list state
  const [conversations, setConversations] = useState([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [selectedConvId, setSelectedConvId] = useState(routeConvId || null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Avatar state machine
  const [avatarExpression, setAvatarExpression] = useState('neutral');
  const [visemes, setVisemes] = useState([]);
  const [spokenText, setSpokenText] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioMuted, setAudioMuted] = useState(false);

  // Active mobile view tab: 'split' (desktop default) | 'avatar' | 'chat'
  const [activeMobileTab, setActiveMobileTab] = useState('chat');

  // Sync route param with internal state
  useEffect(() => {
    if (routeConvId) {
      setSelectedConvId(routeConvId);
    }
  }, [routeConvId]);

  // Fetch optional attached lesson info
  useEffect(() => {
    if (!lessonId) {
      setLessonData(null);
      return;
    }
    getLesson(lessonId)
      .then((data) => setLessonData(data))
      .catch((err) => console.warn('Could not load lesson context:', err));
  }, [lessonId]);

  // Load user's conversations
  const fetchConversations = useCallback(async () => {
    try {
      setLoadingConversations(true);
      const res = await listConversations({ page: 1, page_size: 30 });
      const items = res?.items || (Array.isArray(res) ? res : []);
      setConversations(items);

      // If no conversation is active and conversations exist, select the latest
      if (!selectedConvId && !routeConvId && items.length > 0) {
        setSelectedConvId(items[0].id);
        navigate(`/tutor/${items[0].id}`, { replace: true });
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setLoadingConversations(false);
    }
  }, [selectedConvId, routeConvId, navigate]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Handle new conversation creation
  const handleNewConversation = async () => {
    try {
      const title = lessonData
        ? `Discussion: ${lessonData.title?.slice(0, 24)}...`
        : 'New conversation';
      const created = await createConversation({
        title,
        lesson_id: lessonId || undefined,
      });

      setConversations((prev) => [created, ...prev]);
      setSelectedConvId(created.id);
      navigate(`/tutor/${created.id}`);
      setSidebarOpen(false);
    } catch (err) {
      console.error('Failed to create new conversation:', err);
    }
  };

  // Handle conversation deletion
  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation history?')) return;

    try {
      await deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);

      if (selectedConvId === convId) {
        const nextId = remaining.length > 0 ? remaining[0].id : null;
        setSelectedConvId(nextId);
        if (nextId) {
          navigate(`/tutor/${nextId}`);
        } else {
          navigate('/tutor');
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  // Switch conversation
  const handleSelectConversation = (convId) => {
    setSelectedConvId(convId);
    navigate(`/tutor/${convId}`);
    setSidebarOpen(false);
  };

  // Avatar speech & expression coordination callbacks
  const handleAssistantReply = ({ reply, visemes: vList, expression, text }) => {
    setAvatarExpression(expression || 'explaining');
    setVisemes(vList || []);
    setSpokenText(text || reply || '');
    setIsSpeaking(true);
  };

  const handleThinkingStart = () => {
    setAvatarExpression('thinking');
    setIsSpeaking(false);
    setSpokenText('');
  };

  const handleSpeakMessage = ({ text, expression }) => {
    setAvatarExpression(expression || 'explaining');
    setSpokenText(text);
    setIsSpeaking(true);
  };

  const handleSpeechEnd = () => {
    setIsSpeaking(false);
    setAvatarExpression('neutral');
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Top Header */}
      <PageHeader
        title="AI Avatar Tutor"
        subtitle="Real-time multimodal learning with intelligent lipsync, Socratic dialogue, and tailored explanations."
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setAudioMuted((prev) => !prev)}
              className="flex items-center gap-1.5"
              title={audioMuted ? 'Unmute tutor audio' : 'Mute tutor audio'}
            >
              {audioMuted ? (
                <>
                  <VolumeX className="h-4 w-4 text-red-500" />
                  <span className="text-xs">Unmute</span>
                </>
              ) : (
                <>
                  <Volume2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-xs">Mute Voice</span>
                </>
              )}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="flex items-center gap-1.5 lg:hidden"
            >
              <History className="h-4 w-4" />
              <span className="text-xs">Chats</span>
            </Button>

            <Button
              size="sm"
              onClick={handleNewConversation}
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              <span className="text-xs">New Chat</span>
            </Button>
          </div>
        }
      />

      {/* Mobile Tab Toggle (Avatar / Chat) */}
      <div className="flex rounded-xl bg-slate-100 p-1 lg:hidden dark:bg-slate-800">
        <button
          type="button"
          onClick={() => setActiveMobileTab('chat')}
          className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition-all ${
            activeMobileTab === 'chat'
              ? 'bg-white text-primary-600 shadow-sm dark:bg-slate-700 dark:text-primary-300'
              : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
          }`}
        >
          Chat Stream
        </button>
        <button
          type="button"
          onClick={() => setActiveMobileTab('avatar')}
          className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition-all ${
            activeMobileTab === 'avatar'
              ? 'bg-white text-primary-600 shadow-sm dark:bg-slate-700 dark:text-primary-300'
              : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
          }`}
        >
          Avatar Stage
        </button>
      </div>

      {/* Main Workspace Grid */}
      {/* Fill the viewport rather than a hard-coded 720px: the shell above this
          row (app header + page header + main padding) measures ~15rem, so the
          workspace fits without the page itself scrolling. The min-h floor keeps
          it usable on short screens, where scrolling is the right fallback. */}
      <div className="relative grid grid-cols-1 gap-5 lg:grid-cols-12 lg:h-[calc(100vh-16rem)] lg:min-h-[560px]">
        {/* Collapsible Sidebar (Drawer on mobile, left rail on desktop) */}
        <aside
          className={`fixed inset-y-0 left-0 z-40 w-72 transform bg-white p-4 shadow-xl transition-transform duration-200 ease-in-out dark:bg-slate-900 lg:static lg:z-auto lg:w-auto lg:transform-none lg:col-span-3 lg:rounded-lg lg:border lg:border-slate-200/80 lg:shadow-sm lg:dark:border-slate-800/80 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
        >
          <div className="flex h-full flex-col">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
                <MessageSquare className="h-4 w-4 text-primary-500" />
                <span>Conversations</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNewConversation}
                className="h-8 w-8 p-0"
                title="Create new conversation"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {loadingConversations && (
                <div className="flex h-32 items-center justify-center">
                  <Spinner size="sm" />
                </div>
              )}

              {!loadingConversations && conversations.length === 0 && (
                <div className="py-8 text-center text-xs text-slate-400">
                  No conversations yet. Start chatting below!
                </div>
              )}

              {!loadingConversations &&
                conversations.map((conv) => {
                  const isActive = conv.id === selectedConvId;
                  return (
                    <div
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv.id)}
                      className={`group relative flex cursor-pointer items-center justify-between rounded-xl px-3 py-2.5 text-xs transition-all ${
                        isActive
                          ? 'bg-primary-50 font-medium text-primary-700 dark:bg-primary-950/40 dark:text-primary-300'
                          : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60'
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <p className="truncate">{conv.title || 'Untitled chat'}</p>
                        <span className="text-[10px] text-slate-400">
                          {new Date(conv.updated_at || conv.created_at).toLocaleDateString(
                            [],
                            { month: 'short', day: 'numeric' }
                          )}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => handleDeleteConversation(e, conv.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition-opacity"
                        title="Delete conversation"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
            </div>

            {/* Lesson Context Tag if active */}
            {lessonData && (
              <div className="mt-3 rounded-xl border border-primary-100 bg-primary-50/60 p-2.5 text-xs text-primary-800 dark:border-primary-900/40 dark:bg-primary-950/30 dark:text-primary-300">
                <div className="flex items-center gap-1.5 font-medium">
                  <BookOpen className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{lessonData.title}</span>
                </div>
                <p className="mt-0.5 text-[11px] opacity-80">Linked course lesson</p>
              </div>
            )}
          </div>
        </aside>

        {/* Mobile backdrop for drawer */}
        {sidebarOpen && (
          <div
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-xs lg:hidden"
          />
        )}

        {/* Center/Left: Avatar Stage */}
        <div
          className={`h-[620px] flex-col gap-3 lg:col-span-4 lg:h-full lg:flex ${
            activeMobileTab === 'avatar' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          <div className="flex-1 flex flex-col rounded-lg border border-slate-200/80 bg-white shadow-sm overflow-hidden dark:border-slate-800/80 dark:bg-slate-900">
            {/* Stage header info */}
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 text-xs dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div
                  className={`h-2 w-2 rounded-full ${
                    isSpeaking ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                  }`}
                />
                <span className="font-medium text-slate-700 dark:text-slate-200">
                  Nova · Socratic Tutor
                </span>
              </div>
              <Badge tone={isSpeaking ? 'primary' : 'neutral'}>
                {isSpeaking ? 'Narrating' : 'Ready'}
              </Badge>
            </div>

            {/* Avatar visual canvas & lipsync */}
            {/* AvatarStage is aspect-square, so its height tracks its width.
                min-h-0 lets this row shrink inside the fixed-height column, and
                the max-w cap stops the square from outgrowing the space it has. */}
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden p-3 bg-gradient-to-b from-slate-50 to-white dark:from-slate-900/50 dark:to-slate-900">
              <div className="w-full max-w-[320px]">
                <AvatarStage
                  expression={avatarExpression}
                  visemes={visemes}
                  spokenText={spokenText}
                  isSpeaking={isSpeaking}
                  onSpeechEnd={handleSpeechEnd}
                  audioMuted={audioMuted}
                  onToggleMute={() => setAudioMuted((prev) => !prev)}
                />
              </div>
            </div>

            {/* Avatar Persona Card */}
            <div className="border-t border-slate-100 bg-slate-50/50 p-3.5 text-xs dark:border-slate-800 dark:bg-slate-900/60">
              <div className="flex items-start gap-2">
                <Sparkles className="h-4 w-4 text-primary-500 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-semibold text-slate-800 dark:text-slate-200">
                    Socratic AI Guide
                  </h4>
                  <p className="mt-0.5 text-slate-500 dark:text-slate-400 text-[11px] leading-relaxed">
                    Trained to unpack mental models, diagnose misunderstandings, and
                    guide you toward solutions through questioning.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Chat Panel */}
        <div
          className={`lg:col-span-5 h-[620px] lg:h-full ${
            activeMobileTab === 'chat' ? 'block' : 'hidden lg:block'
          }`}
        >
          <ChatPanel
            conversationId={selectedConvId}
            onConversationCreated={(newConv) => {
              setConversations((prev) => [newConv, ...prev]);
              setSelectedConvId(newConv.id);
              navigate(`/tutor/${newConv.id}`, { replace: true });
            }}
            onAssistantReply={handleAssistantReply}
            onThinkingStart={handleThinkingStart}
            onSpeakMessage={handleSpeakMessage}
            lessonId={lessonId}
            lessonTitle={lessonData?.title}
          />
        </div>
      </div>
    </div>
  );
}
