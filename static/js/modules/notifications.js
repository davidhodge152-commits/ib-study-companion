/**
 * Notification system — bell badge, panel, mark read.
 */

import { api } from './api.js';
import { escapeHtml } from './utils.js';

export function loadNotifications() {
    api.get('/api/notifications')
        .then(res => res.json())
        .then(data => {
            updateNotifBadge(data.unread_count);
            renderNotifications(data.notifications);

            if (data.unread_count > 0 && 'Notification' in window && Notification.permission === 'granted') {
                const newest = data.notifications.find(n => !n.read);
                if (newest && !sessionStorage.getItem('notif_shown_' + newest.id)) {
                    new Notification('IB Study Companion', {
                        body: newest.title,
                        icon: '/static/icons/icon-192.png',
                    });
                    sessionStorage.setItem('notif_shown_' + newest.id, '1');
                }
            }
        })
        .catch(() => {});
}

function updateNotifBadge(count) {
    const badge = document.getElementById('notif-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notif-list');
    if (!list) return;

    if (!notifications || notifications.length === 0) {
        list.innerHTML = '<p class="text-xs text-slate-500 text-center py-4">No notifications</p>';
        return;
    }

    const iconMap = {
        flashcard_due: '&#128196;',
        streak_risk: '&#128293;',
        weekly_summary: '&#128200;',
        plan_reminder: '&#128197;',
        milestone_due: '&#9200;',
        achievement: '&#127942;',
    };

    list.innerHTML = notifications.map(n => `
        <div class="px-3 py-2.5 hover:bg-slate-700/50 cursor-pointer ${n.read ? 'opacity-60' : ''}"
             onclick="${n.action_url ? `window.location='${n.action_url}'` : `markNotificationRead('${n.id}')`}">
            <div class="flex items-start gap-2">
                <span class="text-sm mt-0.5">${iconMap[n.type] || '&#128276;'}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-slate-200 ${n.read ? '' : 'text-white'}">${escapeHtml(n.title)}</p>
                    <p class="text-xs text-slate-400 mt-0.5 truncate">${escapeHtml(n.body)}</p>
                    <p class="text-[10px] text-slate-500 mt-0.5">${n.created_at ? n.created_at.slice(0, 10) : ''}</p>
                </div>
                ${!n.read ? '<span class="w-2 h-2 bg-indigo-500 rounded-full flex-shrink-0 mt-1"></span>' : ''}
            </div>
        </div>
    `).join('');
}

export function toggleNotificationPanel() {
    const panel = document.getElementById('notif-panel');
    if (panel) {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            loadNotifications();
        }
    }
}

export function markNotificationRead(id) {
    api.post('/api/notifications/read', { id })
        .then(() => loadNotifications());
}

export function markAllNotificationsRead() {
    api.post('/api/notifications/read', { id: 'all' })
        .then(() => loadNotifications());
}

export function requestNotificationPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// ── Push notification subscription ──────────────────────────────
export async function subscribeToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
        const reg = await navigator.serviceWorker.ready;
        const existing = await reg.pushManager.getSubscription();
        if (existing) return; // Already subscribed

        // Get VAPID public key from server
        const res = await fetch('/api/push/vapid-key');
        const { publicKey } = await res.json();
        if (!publicKey) return;

        // Convert VAPID key
        const urlBase64ToUint8Array = (base64String) => {
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
            return outputArray;
        };

        const subscription = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicKey),
        });

        await fetch('/api/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subscription: subscription.toJSON() }),
        });
    } catch (e) {
        console.warn('Push subscription failed:', e);
    }
}

// Load notifications on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    loadNotifications();
    // Auto-subscribe to push if notification permission is granted
    if ('Notification' in window && Notification.permission === 'granted') {
        subscribeToPush();
    }
});
