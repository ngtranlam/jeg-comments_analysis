// TikTok Comments Crawler - Content Script
class TikTokCrawlerButton {
  constructor() {
    this.isProcessing = false;
    this.currentVideoId = null;
    this.progressDialog = null;
    this.universalDialog = null;
    this.currentTaskStats = null;
    this.currentAnalysisId = null;
    this.currentAnalysisHtml = null;
    this.typewriterTimeout = null;
    this.customAnalysisRequest = null;
    this.API_BASE = 'https://tiktok-comments-crawler.onrender.com';
    
    this.init();
  }

  init() {
    this.createFloatingButton();
    this.detectVideoChanges();
    this.setupMessageListener();
  }

  createFloatingButton() {
    // Remove existing button if any
    const existingBtn = document.getElementById('tiktok-crawler-btn');
    if (existingBtn) existingBtn.remove();

    // Create floating button
    const button = document.createElement('div');
    button.id = 'tiktok-crawler-btn';
    button.className = 'tiktok-crawler-floating-btn';
    button.innerHTML = `
      <div class="crawler-btn-icon">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2"/>
          <path d="M12 8V16M8 12H16" stroke="currentColor" stroke-width="2"/>
        </svg>
      </div>
      <span class="crawler-btn-text">Analysis</span>
    `;

    // Add click handler
    button.addEventListener('click', () => this.handleCrawlClick());
    
    // Add to page
    document.body.appendChild(button);
    
    // Auto-hide/show based on video detection
    this.updateButtonVisibility();
  }

  detectVideoChanges() {
    // Monitor URL changes for SPA navigation
    let currentUrl = window.location.href;
    
    const observer = new MutationObserver(() => {
      if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        this.updateButtonVisibility();
        this.extractVideoId();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Initial check
    this.extractVideoId();
  }

  extractVideoId() {
    const url = window.location.href;
    const videoMatch = url.match(/\/video\/(\d+)/);
    
    if (videoMatch) {
      this.currentVideoId = videoMatch[1];
      console.log('Detected TikTok Video ID:', this.currentVideoId);
    } else {
      this.currentVideoId = null;
    }
    
    this.updateButtonVisibility();
  }

  updateButtonVisibility() {
    const button = document.getElementById('tiktok-crawler-btn');
    if (!button) return;

    if (this.currentVideoId && !this.isProcessing) {
      button.style.display = 'flex';
      button.classList.remove('disabled');
    } else if (this.isProcessing) {
      button.style.display = 'flex';
      button.classList.add('disabled');
    } else {
      button.style.display = 'none';
    }
  }

  async handleCrawlClick() {
    if (!this.currentVideoId || this.isProcessing) return;

    this.isProcessing = true;
    this.updateButtonVisibility();
    
    try {
      await this.startCrawling();
    } catch (error) {
      console.error('Crawling failed:', error);
      this.showError(error.message);
    } finally {
      this.isProcessing = false;
      this.updateButtonVisibility();
    }
  }

  async startCrawling() {
    // Show universal dialog in crawling state
    this.showUniversalDialog('crawling');
    
    try {
      // Start crawling via API
      const response = await fetch(`${this.API_BASE}/crawl/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: this.currentVideoId,
          video_url: window.location.href
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const result = await response.json();
      const taskId = result.task_id;

      // Poll for progress
      await this.pollProgress(taskId);
      
    } catch (error) {
      this.hideProgressDialog();
      throw error;
    }
  }

  async pollProgress(taskId) {
    const pollInterval = 1000; // 1 second
    
    const poll = async () => {
      try {
        const response = await fetch(`${this.API_BASE}/crawl/status/${taskId}`);
        const status = await response.json();
        
        this.updateProgress(status);
        
        if (status.status === 'completed') {
          this.handleCrawlComplete(status);
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Crawling failed');
        } else if (status.status === 'cancelled') {
          this.hideProgressDialog();
        } else {
          // Continue polling
          setTimeout(poll, pollInterval);
        }
        
      } catch (error) {
        this.hideProgressDialog();
        throw error;
      }
    };
    
    await poll();
  }

  showProgressDialog() {
    // Remove existing dialog
    this.hideProgressDialog();

    // Create progress dialog
    const dialog = document.createElement('div');
    dialog.id = 'tiktok-crawler-progress';
    dialog.className = 'crawler-progress-dialog';
    dialog.innerHTML = `
      <div class="crawl-content">
        <div class="crawl-header">
          <h3>Getting reviews...</h3>
          <button class="crawl-close" id="cancel-crawl">×</button>
        </div>
        
        <div class="crawl-body">
          <div class="crawl-status">
            <p id="crawl-status-text">Navigating to video comments...</p>
          </div>
          
          <div class="crawl-progress-container">
            <div class="crawl-progress-bar">
              <div class="crawl-progress-fill" id="crawl-progress-fill"></div>
            </div>
          </div>
          
          <div class="crawl-stats">
            <span id="crawl-stats-text">★: 0/0</span>
          </div>
        </div>
        
        <div class="progress-footer">
          <button class="btn btn-cancel" id="cancel-btn">Cancel</button>
        </div>
      </div>
    `;

    document.body.appendChild(dialog);
    this.progressDialog = dialog;

    // Add cancel handler
    dialog.querySelector('#cancel-btn').addEventListener('click', () => {
      this.cancelCrawling();
    });
    
    dialog.querySelector('#cancel-crawl').addEventListener('click', () => {
      this.cancelCrawling();
    });

    // Start timer
    this.startTimer();
  }

  hideProgressDialog() {
    if (this.progressDialog) {
      this.progressDialog.remove();
      this.progressDialog = null;
    }
    
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  updateProgress(status) {
    console.log('📊 Updating crawling progress:', status.progress + '%');
    
    // Update universal dialog with crawling data
    this.updateUniversalDialog('crawling', {
      progress: status.progress || 0,
      stats: status.stats || {}
    });
  }

  startTimer() {
    let seconds = 0;
    this.timer = setInterval(() => {
      seconds++;
      const timeElement = this.progressDialog?.querySelector('#elapsed-time');
      if (timeElement) {
        timeElement.textContent = `${seconds}s`;
      }
    }, 1000);
  }

  async cancelCrawling() {
    // Send cancel request to API
    try {
      await fetch(`${this.API_BASE}/crawl/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
    } catch (error) {
      console.error('Cancel request failed:', error);
    }
    
    this.hideProgressDialog();
    this.isProcessing = false;
    this.updateButtonVisibility();
  }

  handleCrawlComplete(status) {
    this.hideProgressDialog();
    
    // Show success dialog
    this.showResultDialog(status);
  }

  showResultDialog(status) {
    console.log('🎯 Crawl completed, transitioning to analysis...');
    console.log('📊 Status received:', status);
    
    // Save crawl stats for use in analysis
    this.currentTaskStats = status.stats;
    console.log('💾 Saved crawl stats:', this.currentTaskStats);
    
    // Switch universal dialog to analyzing state
    console.log('🔄 Switching to analyzing state...');
    this.updateUniversalDialog('analyzing', {
      progress: 0,
      commentCount: status.stats?.comments || 100
    });
    
    // Start analysis immediately
    console.log('⏰ Starting analysis in 1 second...');
    setTimeout(async () => {
      try {
        console.log('🚀 Auto-starting analysis NOW...');
        
        // Retrieve saved custom analysis request from storage
        try {
          const result = await chrome.storage.local.get('analysisRequest');
          if (result.analysisRequest && result.analysisRequest.trim()) {
            this.customAnalysisRequest = result.analysisRequest.trim();
            console.log('📝 Retrieved custom analysis request:', this.customAnalysisRequest);
          } else {
            this.customAnalysisRequest = null;
            console.log('📝 No custom analysis request found, using default');
          }
        } catch (error) {
          console.warn('⚠️ Failed to retrieve custom analysis request:', error);
          this.customAnalysisRequest = null;
        }
        
        await this.startAnalysis(status.task_id);
      } catch (error) {
        console.error('❌ Auto analysis failed:', error);
        this.showError(`Analysis failed: ${error.message}`);
      }
    }, 1000);
  }

  showError(message) {
    const errorDialog = document.createElement('div');
    errorDialog.className = 'crawler-error-dialog';
    errorDialog.innerHTML = `
      <div class="error-content">
        <div class="error-header">
          <h3>❌ Crawling Failed</h3>
          <button class="error-close">×</button>
        </div>
        <div class="error-body">
          <p>${message}</p>
        </div>
      </div>
    `;

    document.body.appendChild(errorDialog);

    errorDialog.querySelector('.error-close').addEventListener('click', () => {
      errorDialog.remove();
    });

    setTimeout(() => {
      if (errorDialog.parentNode) {
        errorDialog.remove();
      }
    }, 5000);
  }

  async startAnalysis(taskId) {
    try {
      console.log('🔬 Starting analysis for task:', taskId);
      console.log('🌐 API Base:', this.API_BASE);
      
      // Start analysis
      console.log('📡 Sending analysis request...');
      const requestBody = {
        task_id: taskId
      };
      
      // Add custom analysis request if provided
      if (this.customAnalysisRequest) {
        requestBody.custom_analysis = this.customAnalysisRequest;
        console.log('🎯 Using custom analysis request:', this.customAnalysisRequest);
      }
      
      const response = await fetch(`${this.API_BASE}/analyze/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('📨 Response status:', response.status);
      console.log('📨 Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error:', errorText);
        throw new Error(`Failed to start analysis: ${response.status} - ${errorText}`);
      }

      const analysisResponse = await response.json();
      this.currentAnalysisId = analysisResponse.analysis_id;
      
      console.log('✅ Analysis started successfully:', analysisResponse);
      console.log('🆔 Analysis ID:', this.currentAnalysisId);
      
      // Universal dialog is already in analyzing state, just start polling
      console.log('🔄 Starting analysis progress polling...');
      this.pollAnalysisProgress();
      
    } catch (error) {
      console.error('💥 Failed to start analysis:', error);
      console.error('💥 Error details:', error.message);
      console.error('💥 Error stack:', error.stack);
      this.showError(`Analysis failed: ${error.message}`);
    }
  }

  showAnalysisProgressDialog() {
    console.log('Creating analysis progress dialog...');
    
    // Remove existing dialogs
    const existing = document.getElementById('tiktok-analysis-progress');
    if (existing) {
      console.log('Removing existing analysis dialog');
      existing.remove();
    }

    // Also remove crawl dialog if still exists
    const crawlDialog = document.getElementById('tiktok-crawler-progress');
    if (crawlDialog) {
      console.log('Removing crawl dialog');
      crawlDialog.remove();
    }

    const dialog = document.createElement('div');
    dialog.id = 'tiktok-analysis-progress';
    dialog.className = 'crawler-analysis-dialog';
    
    console.log('Analysis dialog element created with className:', dialog.className);
    dialog.innerHTML = `
      <div class="analysis-content">
        <div class="analysis-header">
          <h3>Analyzing Comments...</h3>
          <button class="analysis-close" id="cancel-analysis">×</button>
        </div>
        
        <div class="analysis-body">
          <div class="analysis-loading">
            <div class="loading-dots">
              <div class="dot"></div>
              <div class="dot"></div>
              <div class="dot"></div>
            </div>
          </div>
          
          <div class="analysis-status">
            <h4 id="analysis-main-text">Analyzing 0 reviews...</h4>
            <p id="analysis-step1">Processing review data</p>
            <p id="analysis-step2">AI is generating insights</p>
            <p id="analysis-step3">This may take 30-60 seconds</p>
          </div>
        </div>
      </div>
    `;

    console.log('📄 Analysis dialog HTML set, about to append to body...');
    console.log('📄 Dialog innerHTML length:', dialog.innerHTML.length);
    document.body.appendChild(dialog);
    console.log('✅ Analysis dialog appended to body successfully');
    
    // Force a reflow to ensure it's rendered
    dialog.offsetHeight;
    console.log('🔄 Forced reflow completed');
    
    // Check if it's actually in the DOM
    const checkDialog = document.getElementById('tiktok-analysis-progress');
    console.log('🔍 Dialog check after append:', checkDialog ? 'Found in DOM ✅' : 'NOT FOUND ❌');
    
    // Check computed styles
    const computedStyle = window.getComputedStyle(dialog);
    console.log('🎨 Dialog display:', computedStyle.display);
    console.log('🎨 Dialog visibility:', computedStyle.visibility);
    console.log('🎨 Dialog opacity:', computedStyle.opacity);
    
    // Add styles directly if needed
    dialog.style.display = 'flex';
    dialog.style.position = 'fixed';
    dialog.style.top = '0';
    dialog.style.left = '0';
    dialog.style.width = '100%';
    dialog.style.height = '100%';
    dialog.style.zIndex = '20000';
    dialog.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    
    console.log('🎨 Analysis dialog styles applied');
    console.log('🎨 Final dialog display:', dialog.style.display);
    
    // Count total dialogs in DOM
    const allDialogs = document.querySelectorAll('[id*="tiktok"], [class*="crawler"], [class*="analysis"]');
    console.log('📊 Total dialogs in DOM:', allDialogs.length);
    allDialogs.forEach((d, i) => {
      console.log(`📊 Dialog ${i + 1}:`, d.id || d.className);
    });

    // Add cancel handler
    const cancelBtn = dialog.querySelector('#cancel-analysis');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        console.log('Analysis cancel button clicked');
        this.cancelAnalysis();
      });
      console.log('Cancel button handler added');
    } else {
      console.error('Cancel button not found!');
    }
  }

  async pollAnalysisProgress() {
    if (!this.currentAnalysisId) return;

    try {
      const response = await fetch(`${this.API_BASE}/analyze/status/${this.currentAnalysisId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get analysis status: ${response.status}`);
      }

      const status = await response.json();
      console.log('Analysis status:', status);

      // Update progress UI
      this.updateAnalysisProgress(status);

      if (status.status === 'completed') {
        // Analysis completed successfully
        console.log('✅ Analysis completed, showing results...');
        this.currentAnalysisHtml = status.result?.analysis_html || 'No analysis content available';
        this.updateUniversalDialog('results', {
          analysisHtml: this.currentAnalysisHtml
        });
      } else if (status.status === 'failed') {
        // Analysis failed
        console.log('❌ Analysis failed:', status.error);
        this.hideUniversalDialog();
        this.showError(`Analysis failed: ${status.error || 'Unknown error'}`);
      } else if (status.status === 'cancelled') {
        // Analysis cancelled
        console.log('🚫 Analysis cancelled');
        this.hideUniversalDialog();
      } else {
        // Still running, continue polling
        setTimeout(() => this.pollAnalysisProgress(), 2000);
      }
    } catch (error) {
      console.error('Error polling analysis progress:', error);
      this.hideAnalysisProgressDialog();
      this.showError(`Analysis error: ${error.message}`);
    }
  }

  updateAnalysisProgress(status) {
    console.log('🧠 Updating analysis progress:', status.progress + '%');
    
    // Update universal dialog with analysis data
    this.updateUniversalDialog('analyzing', {
      progress: status.progress || 0,
      commentCount: this.currentTaskStats?.comments || status.result?.metadata?.total_comments_analyzed || 100
    });
  }

  hideAnalysisProgressDialog() {
    const dialog = document.getElementById('tiktok-analysis-progress');
    if (dialog) {
      dialog.remove();
    }
  }

  async cancelAnalysis() {
    if (!this.currentAnalysisId) return;

    try {
      const response = await fetch(`${this.API_BASE}/analyze/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysis_id: this.currentAnalysisId
        })
      });

      if (response.ok) {
        console.log('Analysis cancelled');
      }
    } catch (error) {
      console.error('Failed to cancel analysis:', error);
    }

    this.currentAnalysisId = null;
    this.hideAnalysisProgressDialog();
  }

  showAnalysisResultDialog(analysisStatus) {
    const dialog = document.createElement('div');
    dialog.className = 'crawler-analysis-result-dialog';
    dialog.innerHTML = `
            <div class="results-content">
        <div class="results-header">
          <h3>Analysis Results</h3>
          <button class="results-close">×</button>
        </div>
        
        <div class="results-body">
          <div class="results-text">
            <div id="typewriter-content"></div>
          </div>
          
          <div class="results-actions">
            <button class="btn btn-export" id="export-analysis">
              📄 Export to PDF
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(dialog);

    // Add close handler
    dialog.querySelector('.results-close').addEventListener('click', () => {
      dialog.remove();
    });

    // Start typewriter effect
    this.startTypewriterEffect(analysisStatus.result?.analysis_html || 'No analysis content available');

    // Add export handler
    dialog.querySelector('#export-analysis').addEventListener('click', () => {
      // Store current analysis for export
      this.currentAnalysisHtml = analysisStatus.result?.analysis_html || 'No analysis content';
      this.exportToPdf();
      
      // Show success feedback
      const btn = dialog.querySelector('#export-analysis');
      const originalText = btn.textContent;
      btn.textContent = '✅ Generating PDF...';
      setTimeout(() => {
        btn.textContent = originalText;
      }, 3000);
    });

    // Auto remove after 30 seconds (longer for analysis results)
    setTimeout(() => {
      if (dialog.parentNode) {
        dialog.remove();
      }
    }, 30000);
  }

  // Universal Dialog System
  showUniversalDialog(state, data = {}) {
    console.log('🎭 Showing universal dialog in state:', state);
    
    // Remove any existing dialogs
    this.hideUniversalDialog();
    
    // Create new universal dialog
    this.universalDialog = document.createElement('div');
    this.universalDialog.id = 'tiktok-universal-dialog';
    this.universalDialog.className = 'universal-dialog';
    
    // Apply base styles
    this.universalDialog.style.position = 'fixed';
    this.universalDialog.style.top = '0';
    this.universalDialog.style.left = '0';
    this.universalDialog.style.width = '100%';
    this.universalDialog.style.height = '100%';
    this.universalDialog.style.zIndex = '20000';
    this.universalDialog.style.display = 'flex';
    this.universalDialog.style.alignItems = 'center';
    this.universalDialog.style.justifyContent = 'center';
    this.universalDialog.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    this.universalDialog.style.backdropFilter = 'blur(5px)';
    
    // Update content based on state
    this.updateUniversalDialog(state, data);
    
    // Add to DOM
    document.body.appendChild(this.universalDialog);
    console.log('✅ Universal dialog added to DOM');
  }

  updateUniversalDialog(state, data = {}) {
    if (!this.universalDialog) {
      console.error('❌ Universal dialog not found for update');
      return;
    }

    console.log('🔄 Updating universal dialog to state:', state);

    // Check if we need to change state or just update data
    const currentState = this.universalDialog.dataset.currentState;
    
    if (currentState !== state) {
      // State change - need to recreate content
      console.log('🔄 State change from', currentState, 'to', state);
      let content = '';
      
      switch (state) {
        case 'crawling':
          content = this.getCrawlingContent(data);
          break;
        case 'analyzing':
          content = this.getAnalyzingContent(data);
          break;
        case 'results':
          content = this.getResultsContent(data);
          break;
        default:
          console.error('Unknown dialog state:', state);
          return;
      }

      this.universalDialog.innerHTML = content;
      this.universalDialog.dataset.currentState = state;
      
      // Add event listeners based on state
      this.addDialogEventListeners(state);
    } else {
      // Same state - just update specific elements
      console.log('🔄 Updating content for state:', state);
      this.updateDialogContent(state, data);
    }
    
    console.log('✅ Universal dialog updated to:', state);
  }

  updateDialogContent(state, data = {}) {
    if (!this.universalDialog) return;

    switch (state) {
      case 'crawling':
        this.updateCrawlingContent(data);
        break;
      case 'analyzing':
        this.updateAnalyzingContent(data);
        break;
      case 'results':
        // Results don't need incremental updates
        break;
    }
  }

  updateCrawlingContent(data = {}) {
    const progress = data.progress || 0;
    const stats = data.stats || {};
    
    // Update progress bar
    const progressFill = this.universalDialog.querySelector('#progress-fill');
    if (progressFill) {
      progressFill.style.width = `${progress}%`;
    }
    
    // Update status message
    const statusMessage = this.universalDialog.querySelector('#status-message');
    if (statusMessage) {
      statusMessage.textContent = this.getCrawlStatusMessage(progress);
    }
    
    // Update stats
    const statsText = this.universalDialog.querySelector('#stats-text');
    if (statsText) {
      const comments = stats.comments || 0;
      const replies = stats.replies || 0;
      statsText.textContent = `★: ${comments}/${comments + replies}`;
    }
  }

  updateAnalyzingContent(data = {}) {
    const progress = data.progress || 0;
    
    // Update steps based on progress
    const step1 = this.universalDialog.querySelector('#analysis-step1');
    const step2 = this.universalDialog.querySelector('#analysis-step2');  
    const step3 = this.universalDialog.querySelector('#analysis-step3');
    
    if (progress > 30 && step1 && !step1.classList.contains('completed')) {
      step1.classList.add('completed');
    }
    
    if (progress > 60 && step2 && !step2.classList.contains('completed')) {
      step2.classList.add('completed');
    }
    
    if (progress > 90 && step3) {
      if (!step3.classList.contains('completed')) {
        step3.classList.add('completed');
        step3.textContent = 'Almost done...';
      }
    }
  }

  getCrawlingContent(data = {}) {
    const progress = data.progress || 0;
    const stats = data.stats || {};
    
    return `
      <div class="dialog-content">
        <div class="dialog-header">
          <h3>Getting comments...</h3>
          <button class="dialog-close" id="close-dialog">×</button>
        </div>
        
        <div class="dialog-body">
          <div class="status-text">
            <p id="status-message">${this.getCrawlStatusMessage(progress)}</p>
          </div>
          
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" id="progress-fill" style="width: ${progress}%"></div>
            </div>
          </div>
          
          <div class="stats-display">
            <span id="stats-text">★: ${stats.comments || 0}/${(stats.comments || 0) + (stats.replies || 0)}</span>
          </div>
        </div>
      </div>
    `;
  }

  getAnalyzingContent(data = {}) {
    const progress = data.progress || 0;
    const commentCount = this.currentTaskStats?.comments || data.commentCount || 100;
    
    return `
      <div class="dialog-content">
        <div class="dialog-header">
          <h3>Analyzing Comments...</h3>
          <button class="dialog-close" id="close-dialog">×</button>
        </div>
        
        <div class="dialog-body analyzing">
          <div class="loading-animation">
            <div class="loading-dots">
              <div class="dot"></div>
              <div class="dot"></div>
              <div class="dot"></div>
            </div>
          </div>
          
          <div class="analysis-status">
            <h4 id="analysis-main-text">Analyzing ${commentCount} Comments...</h4>
            <p id="analysis-step1" class="${progress > 30 ? 'completed' : ''}">Processing comment data</p>
            <p id="analysis-step2" class="${progress > 60 ? 'completed' : ''}">System is generating insights</p>
            <p id="analysis-step3" class="${progress > 90 ? 'completed' : ''}">${progress > 90 ? 'Almost done...' : 'This may take 30-60 seconds'}</p>
          </div>
        </div>
      </div>
    `;
  }

  getResultsContent(data = {}) {
    const analysisHtml = data.analysisHtml || 'No analysis content available';
    
    return `
      <div class="dialog-content results">
        <div class="dialog-header">
          <h3>Analysis Results</h3>
          <button class="dialog-close" id="close-dialog">×</button>
        </div>
        
        <div class="dialog-body">
          <div class="results-text">
            <div id="typewriter-content"></div>
          </div>
        </div>
        
        <div class="floating-download-btn">
          <button class="btn btn-view" id="view-report">
            View Report
          </button>
          <button class="btn btn-export" id="export-pdf">
            Download PDF
          </button>
        </div>
      </div>
    `;
  }

  getCrawlStatusMessage(progress) {
    if (progress < 30) return 'Navigating to video comments...';
    if (progress < 70) return 'Getting comments data...';
    return 'Processing replies...';
  }

  addDialogEventListeners(state) {
    // Close button
    const closeBtn = this.universalDialog.querySelector('#close-dialog');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        this.hideUniversalDialog();
        this.isProcessing = false;
        this.updateButtonVisibility();
      });
    }

    // State-specific listeners
    if (state === 'results') {
      // Start typewriter effect for results
      const analysisHtml = this.currentAnalysisHtml;
      if (analysisHtml) {
        this.startTypewriterEffect(analysisHtml);
      }

      // View Report button
      const viewBtn = this.universalDialog.querySelector('#view-report');
      if (viewBtn) {
        viewBtn.addEventListener('click', async () => {
          await this.viewReport();
        });
      }

      // PDF Export button
      const exportBtn = this.universalDialog.querySelector('#export-pdf');
      if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
          await this.exportToPdf();
        });
      }
    }
  }

  hideUniversalDialog() {
    // Stop typewriter animation
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
      this.typewriterTimeout = null;
    }
    
    if (this.universalDialog) {
      this.universalDialog.remove();
      this.universalDialog = null;
      console.log('🗑️ Universal dialog removed');
    }
    
    // Also remove any old dialogs
    const oldDialogs = document.querySelectorAll('#tiktok-crawler-progress, #tiktok-analysis-progress, .crawler-result-dialog, .crawler-analysis-result-dialog');
    oldDialogs.forEach(dialog => dialog.remove());
  }

    startTypewriterEffect(htmlContent) {
    const container = document.getElementById('typewriter-content');
    if (!container) {
      console.error('Typewriter container not found!');
      return;
    }

    console.log('🎬 Starting typewriter effect with content length:', htmlContent.length);

    // Clean HTML content and remove title
    const cleanHtml = this.cleanAnalysisHtml(htmlContent);
    
    // Clear container 
    container.innerHTML = '';
    
    // Create a cursor element
    const cursor = document.createElement('span');
    cursor.className = 'typewriter-cursor';
    cursor.textContent = '|';
    container.appendChild(cursor);
    
    // Convert to formatted HTML instead of plain text
    const formattedHtml = this.formatAnalysisContent(cleanHtml);
    
    console.log('⌨️ Starting HTML typewriter effect...');
    this.typeHtmlContent(formattedHtml, container, cursor);
  }

  formatAnalysisContent(cleanHtml) {
    console.log('🎨 Formatting analysis content...');
    
    // Convert plain text to formatted HTML
    let formatted = cleanHtml;
    
    // Format numbered sections (1. 2. 3. etc.)
    formatted = formatted.replace(/^(\d+)\.\s*([^:\n]+)/gm, '<h2 class="section-header">$1. $2</h2>');
    
    // Format subsection headers (letters a. b. c.)
    formatted = formatted.replace(/^([a-z])\.\s*([^:\n]+)/gm, '<h3 class="subsection-header">$1. $2</h3>');
    
    // Format bold categories (UPPERCASE text at start of line)
    formatted = formatted.replace(/^([A-ZÀÁẠÃẢĂẮẰẲẴẶÂẤẦẨẪẬÊÉẸẼẺẾỀỂỄỆÔÓỌÕỎỐỒỔỖỘƠỚỜỞỠỢƯÚỤŨỦỨỪỬỮỰỲÝỴỸỶ\s]+):?\s*/gm, '<h4 class="category-header">$1</h4>');
    
    // Format bullet points
    formatted = formatted.replace(/^[•\-\*]\s*(.+)/gm, '<li class="bullet-item">$1</li>');
    
    // Group consecutive bullet points in lists
    formatted = formatted.replace(/(<li class="bullet-item">.*?<\/li>)(\s*<li class="bullet-item">.*?<\/li>)+/gs, function(match) {
      return '<ul class="bullet-list">' + match + '</ul>';
    });
    
    // Format regular paragraphs
    formatted = formatted.replace(/^(?!<[h2-6]|<li|<ul)(.+)$/gm, function(match, content) {
      if (content.trim()) {
        return '<p class="content-paragraph">' + content.trim() + '</p>';
      }
      return '';
    });
    
    // Add emphasis to keywords in parentheses
    formatted = formatted.replace(/\(([^)]+)\)/g, '<em class="keyword">($1)</em>');
    
    // Format percentage and numbers
    formatted = formatted.replace(/(\d+%|\d+\/\d+)/g, '<span class="number">$1</span>');
    
    // Clean up extra newlines and spaces
    formatted = formatted
      .replace(/\n{3,}/g, '\n\n')
      .replace(/\s+<\/p>/g, '</p>')
      .replace(/<p[^>]*>\s*<\/p>/g, '')
      .trim();
    
    console.log('✅ Content formatted successfully');
    return formatted;
  }

  typeHtmlContent(htmlContent, container, cursor) {
    console.log('⌨️ Starting HTML typing animation...');
    
    // Parse HTML into elements
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlContent;
    
    const elements = Array.from(tempDiv.children);
    let currentElementIndex = 0;
    let currentCharIndex = 0;
    let currentElement = null;
    let currentTextNode = null;
    
    // Clear any existing timeout
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
    }
    
    const typeNextChar = () => {
      // Get current element if needed
      if (!currentElement && currentElementIndex < elements.length) {
        const sourceElement = elements[currentElementIndex];
        currentElement = sourceElement.cloneNode(false); // Clone without children
        currentElement.textContent = ''; // Start empty
        container.insertBefore(currentElement, cursor);
        currentCharIndex = 0;
        
        // Get the text content to type
        currentTextNode = sourceElement.textContent;
        
        console.log(`📝 Starting element: ${sourceElement.tagName} - "${currentTextNode.substring(0, 50)}..."`);
      }
      
      if (currentElement && currentCharIndex < currentTextNode.length) {
        // Add next character to current element
        const char = currentTextNode[currentCharIndex];
        currentElement.textContent += char;
        currentCharIndex++;
        
        // Auto-scroll to keep cursor visible
        this.autoScrollToBottom(cursor);
        
        // Variable typing speed
        const speed = char === ' ' ? 10 : 
                     char === '.' ? 50 : 
                     char === ',' ? 30 : 25;
        
        this.typewriterTimeout = setTimeout(typeNextChar, speed);
        
      } else if (currentElementIndex < elements.length - 1) {
        // Move to next element
        currentElementIndex++;
        currentElement = null;
        currentTextNode = null;
        
        // Small pause between elements
        this.typewriterTimeout = setTimeout(typeNextChar, 100);
        
      } else {
        // Typing completed
        setTimeout(() => {
          if (cursor.parentNode) {
            cursor.remove();
          }
        }, 2000);
        console.log('✅ HTML typewriter effect completed');
      }
    };
    
    typeNextChar();
  }

  autoScrollToBottom(cursor) {
    // Get the results container
    const resultsContainer = document.querySelector('.results-text');
    if (resultsContainer) {
      // Scroll to keep cursor visible
      const cursorRect = cursor.getBoundingClientRect();
      const containerRect = resultsContainer.getBoundingClientRect();
      
      if (cursorRect.bottom > containerRect.bottom - 50) {
        resultsContainer.scrollTop = resultsContainer.scrollHeight - resultsContainer.clientHeight;
      }
    }
  }

  typeText(text, container, cursor) {
    let index = 0;
    const speed = 20; // milliseconds per character
    
    // Clear any existing timeout
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
    }
    
    // Create a text container
    const textContainer = document.createElement('div');
    textContainer.style.whiteSpace = 'pre-wrap'; // Preserve newlines and spaces
    textContainer.style.fontFamily = 'inherit';
    container.insertBefore(textContainer, cursor);
    
    const typeNextChar = () => {
      if (index < text.length) {
        // Get current character
        const char = text[index];
        
        // Add character to text container
        textContainer.textContent += char;
        
        index++;
        
        // Vary speed for more natural typing
        const currentSpeed = char === ' ' ? speed * 0.3 : 
                           char === '\n' ? speed * 1.5 : 
                           char === '.' ? speed * 2 : 
                           char === ',' ? speed * 1.2 : speed;
        
        this.typewriterTimeout = setTimeout(typeNextChar, currentSpeed);
      } else {
        // Typing completed, remove cursor after 2 seconds
        setTimeout(() => {
          if (cursor.parentNode) {
            cursor.remove();
          }
        }, 2000);
        console.log('✅ Typewriter effect completed');
      }
    };
    
    typeNextChar();
  }

  htmlToDisplayText(element) {
    let text = '';
    
    for (let node of element.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        text += node.textContent;
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const tagName = node.tagName.toLowerCase();
        
        // Add appropriate spacing/formatting for different elements
        switch (tagName) {
          case 'h1':
          case 'h2':
          case 'h3':
            text += '\n\n' + node.textContent.toUpperCase() + '\n' + '='.repeat(Math.min(node.textContent.length, 50)) + '\n\n';
            break;
          case 'p':
            text += node.textContent + '\n\n';
            break;
          case 'li':
            text += '• ' + node.textContent + '\n';
            break;
          case 'ul':
          case 'ol':
            // Process list children
            for (let child of node.children) {
              if (child.tagName.toLowerCase() === 'li') {
                text += '• ' + child.textContent + '\n';
              }
            }
            text += '\n';
            break;
          case 'strong':
          case 'b':
            text += node.textContent.toUpperCase();
            break;
          case 'br':
            text += '\n';
            break;
          default:
            // For other elements, just get the text content
            text += node.textContent;
        }
      }
    }
    
    return text.replace(/\n{3,}/g, '\n\n'); // Limit multiple newlines
  }

  cleanAnalysisHtml(htmlContent) {
    console.log('🧹 Cleaning HTML content...');
    console.log('🔍 Original content preview:', htmlContent.substring(0, 200));
    
    // Remove markdown code blocks first
    let cleaned = htmlContent
      .replace(/```html/gi, '') // Remove markdown html blocks
      .replace(/```css/gi, '') // Remove CSS code blocks
      .replace(/```/gi, '') // Remove remaining markdown blocks
      .trim();

    // Remove ALL CSS content - more aggressive approach
    cleaned = cleaned
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '') // Remove style tags and ALL content inside
      .replace(/\.[\w-]+\s*{[^}]*}/gi, '') // Remove CSS class rules (.class { ... })
      .replace(/#[\w-]+\s*{[^}]*}/gi, '') // Remove CSS ID rules (#id { ... })
      .replace(/[a-zA-Z][\w-]*\s*{[^}]*}/gi, '') // Remove any CSS rules (element { ... })
      .replace(/background-[^;:\n]*[;:\n]/gi, '') // Remove background properties
      .replace(/[a-zA-Z-]+:\s*[^;}\n]+[;}]/gi, '') // Remove any CSS property: value pairs
      .replace(/\{[^}]*\}/gi, '') // Remove any remaining { ... } blocks
      .trim();

    // Remove isolated CSS property names and values that might be left
    cleaned = cleaned
      .replace(/^(background-|color:|font-|margin:|padding:|border:|width:|height:).*$/gmi, '') // Remove CSS property lines
      .replace(/^(display|position|top|left|right|bottom|z-index|opacity).*$/gmi, '') // Remove more CSS properties
      .replace(/^[a-zA-Z-]+\s*:.*$/gmi, '') // Remove any remaining property: value lines
      .replace(/^[{}].*$/gmi, '') // Remove lines with just braces
      .replace(/^[;].*$/gmi, '') // Remove lines starting with semicolon
      .trim();

    // Remove single character lines (like 'h' or stray characters)
    cleaned = cleaned
      .replace(/^[a-zA-Z]\s*$/gmi, '') // Remove single character lines
      .replace(/^[a-zA-Z]{1,2}\s*$/gmi, '') // Remove 1-2 character lines
      .trim();

    // Remove the specific title
    cleaned = cleaned
      .replace(/<h1[^>]*>.*?Phân Tích Comment.*?Video.*?TikTok.*?POD.*?<\/h1>/gi, '') // Remove title h1
      .replace(/Phân Tích Comment Video TikTok POD/gi, '') // Remove plain text title
      .replace(/phân tích comment video tiktok pod/gi, '') // Remove lowercase version
      .replace(/PHÂN TÍCH COMMENT VIDEO TIKTOK POD/gi, '') // Remove uppercase version
      .replace(/^\s*={5,}\s*$/gm, '') // Remove title underlines
      .replace(/^\s*-{5,}\s*$/gm, '') // Remove title underlines
      .trim();

    // Remove AI introduction text - more comprehensive patterns
    cleaned = cleaned
      .replace(/^Chắc chắn rồi!.*$/gmi, '') // Remove "Chắc chắn rồi!" line
      .replace(/Chắc chắn rồi!.*?(?=\n|\r|$)/gi, '') // Remove any "Chắc chắn rồi!" sentence
      .replace(/Chào bạn.*?TikTok US\..*?(?=\n|\r|$)/gi, '') // Remove greeting sentence
      .replace(/Dưới đây là.*?phân tích chi tiết.*?(?=\n|\r|$)/gi, '') // Remove analysis description
      .replace(/Với vai trò.*?chuyên gia.*?POD.*?(?=\n|\r|$)/gi, '') // Remove role intro
      .replace(/^.*?chuyên gia R&D.*?POD.*?(?=\n|\r|$)/gmi, '') // Remove any R&D expert intro
      .replace(/^.*?tôi sẽ phân tích.*?comment.*?(?=\n|\r|$)/gmi, '') // Remove analysis promise
      .replace(/^.*?insight.*?hành động cụ thể.*?(?=\n|\r|$)/gmi, '') // Remove insight promise
      .replace(/^.*?áp dụng nguyên tắc.*?Việt Nam.*?(?=\n|\r|$)/gmi, '') // Remove Vietnam reference
      .replace(/^\s*$/gm, '') // Remove empty lines
      .trim();

    // Final cleanup - remove empty lines and normalize spacing
    cleaned = cleaned
      .replace(/^\s*\n/gm, '') // Remove empty lines
      .replace(/\n{3,}/g, '\n\n') // Limit multiple newlines to maximum 2
      .replace(/^\s+/gm, '') // Remove leading spaces from lines
      .trim();

    console.log('🔍 Cleaned content preview:', cleaned.substring(0, 300));
    console.log('🔍 Cleaned content lines (first 10):');
    const lines = cleaned.split('\n').slice(0, 10);
    lines.forEach((line, i) => {
      console.log(`Line ${i}: "${line}"`);
    });
    console.log('✅ Content cleaned and CSS completely removed');
    return cleaned;
  }



  async getUserName() {
    try {
      const result = await chrome.storage.local.get(['userData']);
      if (result.userData && result.userData.name) {
        return result.userData.name;
      }
      return 'Unknown User';
    } catch (error) {
      console.error('Error getting user name:', error);
      return 'Unknown User';
    }
  }

  async viewReport() {
    console.log('👁️ Opening report view...');
    
    if (!this.currentAnalysisHtml) {
      alert('No analysis content to view');
      return;
    }
    
    const userName = await this.getUserName();
    
    // Create a new window with the content for viewing
    const viewWindow = window.open('', '_blank');
    
    // Create a styled HTML document for viewing
    const htmlDoc = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>TikTok Analysis Report</title>
        <style>
          body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            margin: 0;
            padding: 20px;
            color: #333;
            background: white;
            width: 100%;
          }
          
          .header {
            text-align: center;
            border-bottom: 3px solid #f97316;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          
          .header h1 { 
            color: #f97316; 
            margin: 0;
            font-size: 28px;
            font-weight: 700;
          }
          
          .meta-info {
            background: #f8fafc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #f97316;
          }
          
          h1, h2, h3, h4 { 
            color: #1f2937; 
            margin-top: 25px;
            margin-bottom: 15px;
          }
          
          h1 { font-size: 24px; }
          h2 { font-size: 20px; color: #f97316; }
          h3 { font-size: 18px; color: #374151; }
          h4 { font-size: 16px; }
          
          /* Beautiful table styling */
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
          }
          
          table th {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
            font-size: 14px;
            border: none;
          }
          
          table td {
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
            font-size: 13px;
            line-height: 1.5;
            border: none;
          }
          
          table tbody tr:nth-child(even) {
            background: #f9fafb;
          }
          
          table tbody tr:nth-child(odd) {
            background: white;
          }
          
          ul, ol { 
            margin: 15px 0; 
            padding-left: 30px; 
          }
          
          li { 
            margin: 8px 0; 
            line-height: 1.5;
          }
          
          strong, b { 
            color: #1f2937; 
            font-weight: 600;
          }
          
          p { 
            margin: 12px 0; 
            text-align: justify;
          }
          
          blockquote {
            border-left: 4px solid #f97316;
            padding-left: 16px;
            margin: 16px 0;
            color: #6b7280;
            font-style: italic;
          }
          
          code {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: #dc2626;
          }
          
          .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 12px;
          }
          

        </style>
             </head>
       <body>
         <div class="header">
          <h1>📊 TikTok Comments Analysis Report</h1>
        </div>
        
        <div class="meta-info">
          <p><strong>📅 Generated:</strong> ${new Date().toLocaleString('vi-VN', {
            year: 'numeric',
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}</p>
          <p><strong>🎯 Seller:</strong> ${userName}</p>
        </div>
        
        <div class="content">
          ${this.cleanAnalysisHtml(this.currentAnalysisHtml)}
        </div>
        
        <div class="footer">
          <p>Generated by JEG Technology - Comment Analysis Tool</p>
          <p>© 2025 JEG Technology. All rights reserved.</p>
        </div>
      </body>
      </html>
    `;
    
    // Write the content to the new window
    viewWindow.document.write(htmlDoc);
    viewWindow.document.close();
    
    // Focus the new window
    viewWindow.focus();
    
    console.log('✅ Report view opened');
  }

  async exportToPdf() {
    console.log('📄 Exporting to PDF...');
    
    if (!this.currentAnalysisHtml) {
      alert('No analysis content to export');
      return;
    }
    
    const userName = await this.getUserName();
    
    // Create a new window with the content for PDF export
    const printWindow = window.open('', '_blank');
    
    // Create a styled HTML document for PDF
    const htmlDoc = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>TikTok Analysis Report</title>
        <style>
          @page {
            margin: 2cm;
            size: A4;
          }
          
          body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            margin: 0;
            padding: 20px;
            color: #333;
            background: white;
          }
          
          .header {
            text-align: center;
            border-bottom: 3px solid #f97316;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          
          .header h1 { 
            color: #f97316; 
            margin: 0;
            font-size: 28px;
            font-weight: 700;
          }
          
          .meta-info {
            background: #f8fafc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #f97316;
          }
          
          h1, h2, h3, h4 { 
            color: #1f2937; 
            margin-top: 25px;
            margin-bottom: 15px;
            page-break-after: avoid;
          }
          
          h1 { font-size: 24px; }
          h2 { font-size: 20px; color: #f97316; }
          h3 { font-size: 18px; color: #374151; }
          h4 { font-size: 16px; }
          
          /* Beautiful table styling for PDF */
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            page-break-inside: avoid;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
          }
          
          table th {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
            font-size: 14px;
            border: none;
          }
          
          table td {
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
            font-size: 13px;
            line-height: 1.5;
            border: none;
          }
          
          table tbody tr:nth-child(even) {
            background: #f9fafb;
          }
          
          table tbody tr:nth-child(odd) {
            background: white;
          }
          
          ul, ol { 
            margin: 15px 0; 
            padding-left: 30px; 
          }
          
          li { 
            margin: 8px 0; 
            line-height: 1.5;
          }
          
          strong, b { 
            color: #1f2937; 
            font-weight: 600;
          }
          
          p { 
            margin: 12px 0; 
            text-align: justify;
          }
          
          blockquote {
            border-left: 4px solid #f97316;
            padding-left: 16px;
            margin: 16px 0;
            color: #6b7280;
            font-style: italic;
          }
          
          code {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: #dc2626;
          }
          
          .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 12px;
          }
          
          /* Print optimizations */
          @media print {
            .no-print { display: none !important; }
            body { margin: 0; }
            h1, h2, h3 { page-break-after: avoid; }
            table { page-break-inside: avoid; }
            tr { page-break-inside: avoid; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>📊 TikTok Comments Analysis Report</h1>
        </div>
        
        <div class="meta-info">
          <p><strong>📅 Generated:</strong> ${new Date().toLocaleString('vi-VN', {
            year: 'numeric',
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}</p>
          <p><strong>🎯 Seller:</strong> ${userName}</p>
        </div>
        
        <div class="content">
          ${this.cleanAnalysisHtml(this.currentAnalysisHtml)}
        </div>
        
        <div class="footer">
          <p>Generated by JEG Technology - Comment Analysis Tool</p>
          <p>© 2025 JEG Technology. All rights reserved.</p>
        </div>
      </body>
      </html>
    `;
    
    // Write the content to the new window
    printWindow.document.write(htmlDoc);
    printWindow.document.close();
    
    // Wait for content to load, then trigger print dialog
    printWindow.onload = () => {
      setTimeout(() => {
        printWindow.print();
        
        // Close the print window after printing (or if user cancels)
        setTimeout(() => {
          printWindow.close();
        }, 1000);
      }, 500);
    };
    
    // Update button state
    const exportBtn = this.universalDialog.querySelector('#export-pdf');
    if (exportBtn) {
      const originalText = exportBtn.textContent;
      exportBtn.textContent = '✅ Generating PDF...';
      setTimeout(() => {
        exportBtn.textContent = originalText;
      }, 3000);
    }
    
    console.log('✅ PDF export initiated');
  }

  htmlToPlainText(html) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Convert HTML elements to plain text with formatting
    const processNode = (node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        return node.textContent;
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const tagName = node.tagName.toLowerCase();
        let text = '';
        
        // Add formatting based on tag
        switch (tagName) {
          case 'h1':
            text = '\n' + '='.repeat(50) + '\n';
            text += node.textContent.toUpperCase();
            text += '\n' + '='.repeat(50) + '\n\n';
            break;
          case 'h2':
            text = '\n' + '-'.repeat(30) + '\n';
            text += node.textContent;
            text += '\n' + '-'.repeat(30) + '\n\n';
            break;
          case 'h3':
            text = '\n*** ' + node.textContent + ' ***\n\n';
            break;
          case 'p':
            text = node.textContent + '\n\n';
            break;
          case 'ul':
          case 'ol':
            for (let child of node.children) {
              text += '• ' + child.textContent + '\n';
            }
            text += '\n';
            break;
          case 'strong':
            text = node.textContent.toUpperCase();
            break;
          default:
            text = node.textContent;
        }
        
        return text;
      }
      return '';
    };
    
    let result = '';
    for (let child of tempDiv.childNodes) {
      result += processNode(child);
    }
    
    return result;
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'getCurrentVideoId') {
        sendResponse({ videoId: this.currentVideoId });
      } else if (request.action === 'startCrawling') {
        // Handle crawling request from popup with custom analysis
        this.handlePopupCrawlRequest(request.customAnalysis);
        sendResponse({ success: true });
      }
    });
  }

  async handlePopupCrawlRequest(customAnalysis) {
    if (!this.currentVideoId || this.isProcessing) return;

    // Store custom analysis for later use
    this.customAnalysisRequest = customAnalysis;
    
    this.isProcessing = true;
    this.updateButtonVisibility();
    
    try {
      await this.startCrawling();
    } catch (error) {
      console.error('Crawling failed:', error);
      this.showError(error.message);
    } finally {
      this.isProcessing = false;
      this.updateButtonVisibility();
    }
  }
}

// Initialize when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new TikTokCrawlerButton();
  });
} else {
  new TikTokCrawlerButton();
} 