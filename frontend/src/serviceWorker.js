// Enhanced Service Worker for PWA with offline caching and push notifications
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, CacheFirst, NetworkFirst } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { BackgroundSyncPlugin } from 'workbox-background-sync';

// Precache all static assets
precacheAndRoute(self.__WB_MANIFEST);

// Clean up old caches
cleanupOutdatedCaches();

// Cache API responses with network-first strategy
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 5 * 60, // 5 minutes
      }),
    ],
  })
);

// Cache images with cache-first strategy
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
      }),
    ],
  })
);

// Cache static assets with stale-while-revalidate
registerRoute(
  ({ request }) =>
    request.destination === 'script' ||
    request.destination === 'style' ||
    request.destination === 'font',
  new StaleWhileRevalidate({
    cacheName: 'static-resources',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
    ],
  })
);

// Background sync for failed API requests
const bgSyncPlugin = new BackgroundSyncPlugin('api-queue', {
  maxRetentionTime: 24 * 60, // Retry for max of 24 hours (specified in minutes)
});

registerRoute(
  ({ url, request }) => 
    url.pathname.startsWith('/api/') && 
    (request.method === 'POST' || request.method === 'PUT' || request.method === 'PATCH'),
  new NetworkFirst({
    cacheName: 'api-mutations',
    plugins: [bgSyncPlugin],
  })
);

// Handle offline fallback
registerRoute(
  ({ request }) => request.mode === 'navigate',
  async ({ event }) => {
    try {
      return await fetch(event.request);
    } catch (error) {
      return caches.match('/offline.html');
    }
  }
);

// Push notification handling
self.addEventListener('push', (event) => {
  const options = {
    body: 'You have new wellness insights available!',
    icon: '/logo192.png',
    badge: '/logo192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1,
    },
    actions: [
      {
        action: 'explore',
        title: 'View Insights',
        icon: '/logo192.png',
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/logo192.png',
      },
    ],
  };

  if (event.data) {
    const payload = event.data.json();
    options.body = payload.body || options.body;
    options.title = payload.title || 'Wellness Platform';
    options.data = { ...options.data, ...payload.data };
  }

  event.waitUntil(
    self.registration.showNotification('Wellness Platform', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/?view=insights')
    );
  } else if (event.action === 'close') {
    // Just close the notification
    return;
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Handle background sync
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    // Sync any pending data when back online
    const cache = await caches.open('api-mutations');
    const requests = await cache.keys();
    
    for (const request of requests) {
      try {
        await fetch(request);
        await cache.delete(request);
      } catch (error) {
        console.log('Background sync failed for request:', request.url);
      }
    }
  } catch (error) {
    console.error('Background sync error:', error);
  }
}

// Handle app updates
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Install event
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  // Force the waiting service worker to become the active service worker
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  event.waitUntil(clients.claim());
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'wellness-data-sync') {
    event.waitUntil(syncWellnessData());
  }
});

async function syncWellnessData() {
  try {
    // Sync critical wellness data in the background
    await fetch('/api/dashboard/stats');
    await fetch('/api/ai-insights/user');
  } catch (error) {
    console.log('Periodic sync failed:', error);
  }
}
