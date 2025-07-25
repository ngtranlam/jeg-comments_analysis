// TikTok Comments Crawler - Background Service Worker

chrome.runtime.onInstalled.addListener(() => {
  console.log('TikTok Comments Crawler installed');
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
  // Check if we're on TikTok
  if (tab.url.includes('tiktok.com')) {
    // Send message to content script
    chrome.tabs.sendMessage(tab.id, {
      action: 'toggleCrawler'
    });
  } else {
    // Show notification if not on TikTok
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/main_icon.png',
      title: 'TikTok Comments Analysis',
      message: 'Please navigate to a TikTok video page to use this extension.'
    });
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  switch (request.action) {
    case 'crawlStarted':
      // Could show notification or update badge
      chrome.action.setBadgeText({
        text: '⏳',
        tabId: sender.tab.id
      });
      break;
      
    case 'crawlCompleted':
      chrome.action.setBadgeText({
        text: '✓',
        tabId: sender.tab.id
      });
      
      // Clear badge after 3 seconds
      setTimeout(() => {
        chrome.action.setBadgeText({
          text: '',
          tabId: sender.tab.id
        });
      }, 3000);
      break;
      
    case 'crawlFailed':
      chrome.action.setBadgeText({
        text: '✗',
        tabId: sender.tab.id
      });
      
      setTimeout(() => {
        chrome.action.setBadgeText({
          text: '',
          tabId: sender.tab.id
        });
      }, 3000);
      break;
  }
});

// Context menu for TikTok videos
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'crawlTikTokComments',
    title: 'Crawl Comments for this Video',
    contexts: ['page'],
    documentUrlPatterns: ['*://*.tiktok.com/*']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'crawlTikTokComments') {
    chrome.tabs.sendMessage(tab.id, {
      action: 'startCrawling'
    });
  }
});

// Storage helpers
const storage = {
  async get(key) {
    const result = await chrome.storage.local.get(key);
    return result[key];
  },
  
  async set(key, value) {
    await chrome.storage.local.set({ [key]: value });
  },
  
  async clear() {
    await chrome.storage.local.clear();
  }
};

// API settings
const API_CONFIG = {
  baseUrl: 'http://localhost:8000',
  timeout: 30000
}; 