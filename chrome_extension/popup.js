// Comment Analysis - Popup Script

class CommentAnalysisPopup {
  constructor() {
    this.API_BASE = 'http://localhost:8000';
    this.currentTab = null;
    this.isLoggedIn = false;
    this.userData = null;
    this.autoSaveTimeout = null;
    
    this.init();
  }

  async init() {
    await this.checkUserLogin();
    await this.getCurrentTab();
    
    if (this.isLoggedIn) {
      await this.showMainContent();
      this.setupMainEventListeners();
    } else {
      this.showLoginForm();
      this.setupLoginEventListeners();
    }
  }

  async getCurrentTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    this.currentTab = tabs[0];
  }

  async checkUserLogin() {
    const userData = await this.getStorageItem('userData');
    if (userData && userData.name && userData.username) {
      this.isLoggedIn = true;
      this.userData = userData;
    }
  }

  showLoginForm() {
    document.getElementById('login-container').classList.remove('hidden');
    document.getElementById('main-content').classList.add('hidden');
    document.getElementById('user-greeting').textContent = 'Welcome!';
  }

  async showMainContent() {
    document.getElementById('login-container').classList.add('hidden');
    document.getElementById('main-content').classList.remove('hidden');
    document.getElementById('user-greeting').textContent = `Hello, ${this.userData.name}!`;
    
    // Load saved analysis request
    await this.loadAnalysisRequest();
  }

  setupLoginEventListeners() {
    const loginForm = document.getElementById('login-form');
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleLogin();
    });
  }

  async handleLogin() {
    const name = document.getElementById('user-name').value.trim();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    if (!name || !username || !password) {
      this.showMessage('Please fill in all fields', 'error');
      return;
    }

    // Show loading
    const loginBtn = document.getElementById('login-btn-text');
    const loginLoading = document.getElementById('login-loading');
    loginBtn.classList.add('hidden');
    loginLoading.classList.remove('hidden');

    try {
      // Simulate login process (bypassing actual authentication)
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Save user data
      const userData = { name, username, loginDate: new Date().toISOString() };
      await this.setStorageItem('userData', userData);
      
      this.isLoggedIn = true;
      this.userData = userData;
      
      // Switch to main content
      await this.showMainContent();
      this.setupMainEventListeners();
      
      this.showMessage('Welcome! Setup completed successfully.', 'success');
      
    } catch (error) {
      console.error('Login error:', error);
      this.showMessage('Setup failed. Please try again.', 'error');
    } finally {
      // Hide loading
      loginBtn.classList.remove('hidden');
      loginLoading.classList.add('hidden');
    }
  }

  setupMainEventListeners() {
    // Save Analysis button
    document.getElementById('save-analysis').addEventListener('click', () => {
      this.saveAnalysisRequest();
    });

    // Reset Analysis button
    document.getElementById('reset-analysis').addEventListener('click', () => {
      this.resetAnalysisRequest();
    });

    // Auto-save on textarea input
    const analysisTextarea = document.getElementById('analysis-request');
    analysisTextarea.addEventListener('input', () => {
      this.scheduleAutoSave();
    });
  }

  async loadAnalysisRequest() {
    const savedRequest = await this.getStorageItem('analysisRequest');
    if (savedRequest) {
      document.getElementById('analysis-request').value = savedRequest;
    }
  }

  async saveAnalysisRequest() {
    const request = document.getElementById('analysis-request').value.trim();
    await this.setStorageItem('analysisRequest', request);
    this.showSaveStatus('💾 Saved successfully!', 'save-success');
  }

  resetAnalysisRequest() {
    document.getElementById('analysis-request').value = '';
    this.setStorageItem('analysisRequest', '');
    this.showSaveStatus('🔄 Reset to default', 'save-success');
  }

  scheduleAutoSave() {
    if (this.autoSaveTimeout) {
      clearTimeout(this.autoSaveTimeout);
    }
    
    this.autoSaveTimeout = setTimeout(async () => {
      const request = document.getElementById('analysis-request').value.trim();
      await this.setStorageItem('analysisRequest', request);
      this.showSaveStatus('✅ Auto-saved', 'save-success');
    }, 2000);
  }

  showSaveStatus(message, className) {
    const saveStatus = document.getElementById('save-status');
    saveStatus.textContent = message;
    saveStatus.className = `save-status ${className}`;
    
    setTimeout(() => {
      saveStatus.textContent = '';
      saveStatus.className = 'save-status';
    }, 3000);
  }

  showMessage(message, type = 'info') {
    // Create temporary notification
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 10px;
      left: 10px;
      right: 10px;
      background: ${type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(34, 197, 94, 0.9)'};
      color: white;
      padding: 12px;
      border-radius: 8px;
      font-size: 14px;
      text-align: center;
      z-index: 1000;
      animation: slideInDown 0.3s ease;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  async getStorageItem(key) {
    const result = await chrome.storage.local.get(key);
    return result[key];
  }

  async setStorageItem(key, value) {
    await chrome.storage.local.set({ [key]: value });
  }
}

// Initialize popup when DOM loads
document.addEventListener('DOMContentLoaded', () => {
  new CommentAnalysisPopup();
});

// Handle messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Popup received message:', request);
  
  if (request.action === 'updateStatus') {
    // Could update UI based on analysis status
  }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInDown {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;
document.head.appendChild(style); 