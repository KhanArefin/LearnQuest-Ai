/**
 * NotificationBell component.
 * OWNER: Member 4.
 *
 * Displays live in-app notifications (badges, challenges, level-ups)
 * with an unread badge, dropdown list, and mark-as-read interaction.
 */
import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, CheckCheck, Sparkles, Trophy, Zap } from 'lucide-react';
import { notifications, markRead, markAllRead } from '../../api/gamification';

function formatRelativeTime(isoStr) {
  if (!isoStr) return '';
  try {
    const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(isoStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

function getNotificationIcon(type) {
  switch (type) {
    case 'badge_earned':
      return <Trophy className="h-4 w-4 text-warning" />;
    case 'challenge_completed':
      return <Zap className="h-4 w-4 text-primary-400" />;
    case 'level_up':
      return <Sparkles className="h-4 w-4 text-easy-fg" />;
    default:
      return <Bell className="h-4 w-4 text-muted" />;
  }
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const bellRef = useRef(null);

  const fetchNotifications = async () => {
    try {
      const res = await notifications();
      if (res) {
        setItems(res.items || []);
        setUnreadCount(res.unread || 0);
      }
    } catch {
      // Gracefully ignore fetch errors
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll notifications every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close when clicked outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (bellRef.current && !bellRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkRead = async (id, e) => {
    e?.stopPropagation();
    try {
      await markRead(id);
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllRead();
      setItems((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Ignore
    }
  };

  return (
    <div className="relative" ref={bellRef}>
      <button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) fetchNotifications();
        }}
        title="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded text-muted transition-colors hover:bg-raised hover:text-hard focus:outline-none"
      >
        <Bell className="h-[18px] w-[18px]" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-500 px-1 text-[10px] font-bold text-white shadow-sm ring-2 ring-canvas">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-11 z-50 w-80 sm:w-96 rounded-xl border border-line bg-surface p-0 shadow-2xl backdrop-blur-md"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-ink">Notifications</span>
                {unreadCount > 0 && (
                  <span className="rounded-full bg-primary-500/10 px-2 py-0.5 text-2xs font-medium text-primary-400">
                    {unreadCount} unread
                  </span>
                )}
              </div>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className="flex items-center gap-1 text-2xs font-medium text-primary-400 transition-colors hover:text-primary-300"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Mark all read
                </button>
              )}
            </div>

            {/* Notification List */}
            <div className="max-h-80 overflow-y-auto divide-y divide-line/40">
              {items.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted">
                  <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-raised text-muted">
                    <Bell className="h-5 w-5" />
                  </div>
                  No notifications yet.
                </div>
              ) : (
                items.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => !item.is_read && handleMarkRead(item.id)}
                    className={`flex items-start gap-3 p-3.5 transition-colors cursor-pointer ${
                      item.is_read ? 'opacity-70 hover:bg-raised/40' : 'bg-primary-950/20 hover:bg-primary-950/30'
                    }`}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-raised">
                      {getNotificationIcon(item.type)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-1">
                        <span
                          className={`text-xs ${
                            item.is_read ? 'font-medium text-ink' : 'font-semibold text-ink'
                          }`}
                        >
                          {item.title}
                        </span>
                        <span className="text-[10px] text-faint">
                          {formatRelativeTime(item.created_at)}
                        </span>
                      </div>
                      {item.body && (
                        <p className="mt-0.5 text-2xs text-body leading-relaxed line-clamp-2">
                          {item.body}
                        </p>
                      )}
                    </div>
                    {!item.is_read && (
                      <span
                        title="Mark as read"
                        onClick={(e) => handleMarkRead(item.id, e)}
                        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-muted hover:bg-raised hover:text-hard"
                      >
                        <span className="h-2 w-2 rounded-full bg-primary-500" />
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
