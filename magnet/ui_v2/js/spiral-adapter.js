/**
 * §SKELETON:CompleteUIModule
 * MAGNET Spiral Adapter
 * 
 * Complete implementation of the design spiral UI integration.
 * Handles: chat, sketch, low confidence, clarification, 409 retry, 
 * partial status, WS resync, GLB retry.
 */

// ClarificationPanel is embedded below since we don't use ES modules in UIv2

class ClarificationPanel {
  constructor(containerEl) {
    this.container = containerEl;
    this._onSubmit = null;
    this._onCancel = null;
    this._requestId = null;
  }

  show({ questions, requestId, onSubmit, onCancel }) {
    this._onSubmit = onSubmit;
    this._onCancel = onCancel;
    this._requestId = requestId;

    this.container.innerHTML = `
      <div class="clarification-panel">
        <div class="clarification-header">
          <h3>🤔 Clarification Needed</h3>
          <p>Please answer the following questions to proceed:</p>
        </div>
        <form id="clarification-form" class="clarification-form">
          ${questions.map((q, i) => this._renderQuestion(q, i)).join('')}
          <div class="clarification-actions">
            <button type="button" class="btn btn-secondary btn-cancel">Cancel</button>
            <button type="submit" class="btn btn-primary btn-submit">Submit Answers</button>
          </div>
        </form>
      </div>
    `;

    this.container.querySelector('.btn-cancel').onclick = () => {
      if (this._onCancel) this._onCancel();
      this.hide();
    };

    this.container.querySelector('#clarification-form').onsubmit = (e) => {
      e.preventDefault();
      this._handleSubmit();
    };

    this.container.style.display = 'block';
    this.container.classList.add('visible');
    
    const firstInput = this.container.querySelector('input, select, textarea');
    if (firstInput) firstInput.focus();
  }

  _renderQuestion(question, index) {
    const { id, text, question: questionText, type, options, required = true, placeholder = '' } = question || {};
    const inputId = `clarification-${id || index}`;
    const inputName = id || `q${index}`;
    const requiredAttr = required ? 'required' : '';
    const labelText = (text ?? questionText ?? '').toString();

    if (type === 'select' && options) {
      const normalized = Array.isArray(options)
        ? options.map(o => (typeof o === 'string' ? { value: o, label: o } : o)).filter(Boolean)
        : [];
      return `
        <div class="clarification-question">
          <label for="${inputId}">${labelText}</label>
          <select id="${inputId}" name="${inputName}" ${requiredAttr}>
            <option value="">-- Select an option --</option>
            ${normalized.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
          </select>
        </div>
      `;
    }

    if (type === 'number') {
      return `
        <div class="clarification-question">
          <label for="${inputId}">${labelText}</label>
          <input type="number" id="${inputId}" name="${inputName}" 
                 placeholder="${placeholder}" ${requiredAttr} step="any" />
        </div>
      `;
    }

    return `
      <div class="clarification-question">
        <label for="${inputId}">${labelText}</label>
        <input type="text" id="${inputId}" name="${inputName}" 
               placeholder="${placeholder}" ${requiredAttr} />
      </div>
    `;
  }

  async _handleSubmit() {
    const form = this.container.querySelector('#clarification-form');
    const formData = new FormData(form);
    const responses = Object.fromEntries(formData.entries());

    const submitBtn = this.container.querySelector('.btn-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
      if (this._onSubmit) {
        await this._onSubmit({ requestId: this._requestId, responses });
      }
    } catch (e) {
      console.error('Clarification submit failed:', e);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Answers';
    }
  }

  hide() {
    this.container.style.display = 'none';
    this.container.classList.remove('visible');
    this.container.innerHTML = '';
    this._onSubmit = null;
    this._onCancel = null;
    this._requestId = null;
  }
}


class SpiralAdapter {
  constructor(options = {}) {
    this.designId = options.designId || null;
    this.baseUrl = options.baseUrl || '';
    this._lastDesignVersion = 0;
    this._spiralIteration = 0;
    this._lastMessage = '';
    this._renderedVersion = null;
    this._activeConstraints = [];
    this._sceneManager = options.sceneManager || window.magnetThreeScene;
    this._panels = options.panels || {};
    this._lastSketchImage = null;
    this._lastSketchAnnotations = '';
    
    // TASK-025: Loading indicator state
    this._loadingStartTime = null;
    this._loadingTimeoutId = null;
    this._loadingPhase = null;

    // Demo reliability: allow long-running LLM/compile/physics.
    // CREATE often requires large JSON artifacts; 60s is routinely too short.
    // Keep this higher to avoid client abort while the server is still working.
    this._requestTimeoutMs = 180000;
    
    // Initialize clarification panel
    const clarificationContainer = document.getElementById('clarificationContainer');
    this._clarificationPanel = clarificationContainer 
      ? new ClarificationPanel(clarificationContainer) 
      : null;
  }

  // ============================================================
  // TASK-025: Loading Indicator Methods
  // ============================================================
  
  _showLoading(phase = 'Thinking...') {
    this._loadingPhase = phase;
    this._loadingStartTime = Date.now();
    
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
      indicator.classList.add('visible');
      indicator.classList.remove('warning');
      const textEl = indicator.querySelector('.loading-text');
      if (textEl) textEl.textContent = phase;
    }
    
    // Disable chat input
    const chatContainer = document.querySelector('.chat-input-container');
    if (chatContainer) chatContainer.classList.add('loading');
    
    // Set timeout warning after 10 seconds
    this._loadingTimeoutId = setTimeout(() => {
      this._showLoadingWarning();
    }, 10000);
  }
  
  _updateLoadingPhase(phase) {
    this._loadingPhase = phase;
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
      const textEl = indicator.querySelector('.loading-text');
      if (textEl) textEl.textContent = phase;
    }
  }
  
  _showLoadingWarning() {
    const indicator = document.getElementById('loadingIndicator');
    if (indicator && indicator.classList.contains('visible')) {
      indicator.classList.add('warning');
      const textEl = indicator.querySelector('.loading-text');
      if (textEl) {
        textEl.textContent = `${this._loadingPhase} (This is taking longer than usual...)`;
      }
    }
  }
  
  _hideLoading() {
    const indicator = document.getElementById('loadingIndicator');
    if (indicator) {
      indicator.classList.remove('visible', 'warning');
    }
    
    // Re-enable chat input
    const chatContainer = document.querySelector('.chat-input-container');
    if (chatContainer) chatContainer.classList.remove('loading');
    
    // Clear timeout
    if (this._loadingTimeoutId) {
      clearTimeout(this._loadingTimeoutId);
      this._loadingTimeoutId = null;
    }
    
    this._loadingStartTime = null;
    this._loadingPhase = null;
  }

  // ============================================================
  // §SKELETON:SpiralChatCall — Main chat entry point
  // ============================================================
  async sendChat(message) {
    if (!this.designId) throw new Error('No design selected');
    
    this._lastMessage = message;
    
    // TASK-025: Show loading indicator
    this._showLoading('Thinking...');
    
    try {
      // Hard timeout to avoid indefinite hangs; align with FIX_PLAN (60s).
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this._requestTimeoutMs);

      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          message,
          constraints: this._activeConstraints,
          expected_version: this._lastDesignVersion || null,
          request_id: crypto?.randomUUID?.() ?? String(Date.now()),
          min_confidence: 0.6,
          force_apply: false,
          // PRODUCTION: default off. Only hydrostatics is a gate; downstream grades
          // should be user-triggered to avoid noisy "partial" banners.
          run_critical_phases: false,
          glb_timeout_ms: 2000,
          glb_retry_limit: 5
        })
      });
      clearTimeout(timeoutId);

      // §SKELETON:409RetryHandler — Handle version conflict
      if (response.status === 409) {
        this._hideLoading();
        return this._handleConflict(response, message);
      }

      if (!response.ok) {
        this._hideLoading();
        throw new Error(`Spiral chat failed: ${response.status}`);
      }

      // TASK-025: Update loading phase
      this._updateLoadingPhase('Compiling geometry...');

      const result = await response.json();
      
      // TASK-025: Update loading phase for physics
      if (result.status === 'applied' || result.status === 'partial') {
        this._updateLoadingPhase('Validating physics...');
      }
      
      const handled = await this._handleSpiralResponse(result);
      
      // TASK-025: Hide loading indicator
      this._hideLoading();
      
      return handled;
    } catch (e) {
      this._hideLoading();
      // Normalize abort into a clearer timeout message.
      const isAbort = (e && (e.name === 'AbortError' || String(e).includes('AbortError')));
      const msg = isAbort
        ? `Request timed out after ${Math.round(this._requestTimeoutMs / 1000)}s. Try again, or simplify the request.`
        : (e.message || String(e));
      this._showErrorFeedback('Request failed', [msg]);
      throw e;
    }
  }

  // ============================================================
  // §SKELETON:ResponseHandler — Route response to appropriate handler
  // ============================================================
  async _handleSpiralResponse(result) {
    // Path B: surface integrity drift warnings and offer one-click repair.
    if (Array.isArray(result.integrity_warnings) && result.integrity_warnings.length > 0) {
      const message = `Design integrity warning:\n- ${result.integrity_warnings.join('\n- ')}`;
      this._showWarningBanner({
        message,
        actions: [
          {
            label: 'Repair Now',
            onClick: async () => {
              try {
                const resp = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/integrity/repair`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    preview_only: false,
                    expected_version: this._lastDesignVersion || null
                  })
                });
                if (!resp.ok) throw new Error(`Repair failed: ${resp.status}`);
                const repair = await resp.json();
                if (repair.applied) {
                  this._showToast('Integrity repair applied', 'success');
                  this._lastDesignVersion = repair.design_version_after;
                  await this._loadHullGeometryWithRetry(repair.design_version_after);
                } else {
                  this._showToast('Integrity repair: no changes needed', 'info');
                }
              } catch (e) {
                this._showToast(`Integrity repair failed: ${e.message}`, 'error');
              }
            }
          },
          { label: 'Dismiss', onClick: () => this._dismissWarning() }
        ]
      });
    }

    switch (result.status) {
      case 'applied':
        this._lastDesignVersion = result.design_version_after;
        this._spiralIteration = result.spiral_iteration;
        this._refreshPhasesFromResponse(result);
        if (result.glb_ready) {
          await this._loadHullGeometryWithRetry(result.design_version_after);
        } else if (result.glb_retry_after_ms) {
          setTimeout(() => this._loadHullGeometryWithRetry(result.design_version_after), result.glb_retry_after_ms);
        }
        this._showSuccessFeedback(result.feedback, result.metrics, result.deltas);
        return result;

      case 'partial':
        this._lastDesignVersion = result.design_version_after;
        this._handlePartialStatus(result);
        return result;

      case 'proposal_low_confidence':
        return this._handleLowConfidence(result);

      case 'needs_clarification':
        return this._handleClarification(result);

      case 'failed':
        this._showErrorFeedback(result.feedback, result.errors);
        return result;

      default:
        console.warn('Unknown spiral status:', result.status);
        this._showErrorFeedback('Unexpected response', [result.status]);
        return result;
    }
  }

  // ============================================================
  // §SKELETON:LowConfidenceHandler — Show proposal for review
  // ============================================================
  async _handleLowConfidence(result) {
    const confirmed = await this._showConfirmationDialog({
      title: 'Low Confidence Proposal',
      message: `Agent confidence: ${(result.average_confidence * 100).toFixed(0)}%`,
      details: result.program_text,
      confirmText: 'Apply Anyway',
      cancelText: 'Refine Request'
    });

    if (confirmed) {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: this._lastMessage,
          expected_version: result.design_version_after,
          force_apply: true,
          request_id: crypto?.randomUUID?.() ?? String(Date.now())
        })
      });
      return this._handleSpiralResponse(await response.json());
    }
    return null;
  }

  // ============================================================
  // §SKELETON:ClarificationHandler — Show clarification form
  // ============================================================
  async _handleClarification(result) {
    // Always show feedback message in terminal/toast first
    if (result.feedback) {
      // Check if this is a timeout-related clarification (don't show full panel, just message)
      const isTimeout = result.feedback.toLowerCase().includes('took too long') || 
                        result.feedback.toLowerCase().includes('timeout');
      if (isTimeout) {
        this._showToast({
          type: 'warning',
          title: '⏱️ Request Timed Out',
          message: result.feedback,
          duration: 8000
        });
        // For timeout, don't show clarification panel - user can just type a new command
        if (!result.requires_confirmation) {
          return result;
        }
      } else {
        this._showToast({
          type: 'info',
          title: 'ℹ️ Clarification Needed',
          message: result.feedback,
          duration: 6000
        });
      }
    }

    if (!this._clarificationPanel) {
      console.error('Clarification panel not initialized');
      // Do not block the UI in "Processing" if the panel isn't available.
      return result;
    }

    // IMPORTANT: do NOT await user input here. Returning a promise that only resolves
    // on submit/cancel keeps the UI "Processing" indefinitely.
    this._clarificationPanel.show({
      questions: Array.isArray(result.clarification_questions) ? result.clarification_questions : [],
      requestId: result.clarification_request_id,
      onSubmit: async ({ responses }) => {
        try {
          if (typeof MagnetStudio?.setStatus === 'function') {
            MagnetStudio.setStatus('Processing', 'processing');
          }
          const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: this._lastMessage,
              expected_version: result.design_version_after,
              clarification_response: { requestId: result.clarification_request_id, responses },
              request_id: crypto?.randomUUID?.() ?? String(Date.now())
            })
          });
          this._clarificationPanel.hide();
          await this._handleSpiralResponse(await response.json());
        } catch (e) {
          console.error('Clarification follow-up failed:', e);
          this._showToast(`Clarification failed: ${e.message || e}`, 'error');
        } finally {
          if (typeof MagnetStudio?.setStatus === 'function') {
            MagnetStudio.setStatus('Ready');
          }
          MagnetStudio?.terminal?.cursor?.();
        }
      },
      onCancel: () => {
        this._clarificationPanel.hide();
        if (typeof MagnetStudio?.setStatus === 'function') {
          MagnetStudio.setStatus('Ready');
        }
        MagnetStudio?.terminal?.cursor?.();
      }
    });

    return result;
  }

  // ============================================================
  // §SKELETON:PartialHandler — Show warning for partial success
  // ============================================================
  _handlePartialStatus(result) {
    const failedList = result.failed_phases.join(', ');
    this._showWarningBanner({
      message: `Applied with warnings. Failed phases: ${failedList}`,
      actions: [
        { label: 'View Details', onClick: () => this._showPhaseErrors(result.failed_phases) },
        { label: 'Continue', onClick: () => this._dismissWarning() }
      ]
    });
    
    if (result.glb_ready) {
      this._loadHullGeometryWithRetry(result.design_version_after);
    }
  }

  // ============================================================
  // §SKELETON:409RetryHandler — Auto-retry on version conflict
  // ============================================================
  async _handleConflict(response, originalMessage) {
    const err = await response.json();
    console.warn('Version conflict:', err.detail);

    this._lastDesignVersion = err.detail.current_version;

    const retryResponse = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: originalMessage,
        expected_version: this._lastDesignVersion,
        request_id: crypto?.randomUUID?.() ?? String(Date.now())
      })
    });

    if (!retryResponse.ok) {
      throw new Error(`Retry failed: ${retryResponse.status}`);
    }

    return this._handleSpiralResponse(await retryResponse.json());
  }

  // ============================================================
  // §SKELETON:GLBRetry — Load GLB with exponential backoff
  // ============================================================
  async _loadHullGeometryWithRetry(version, retryLimit = 5, initialDelayMs = 500) {
    for (let attempt = 0; attempt < retryLimit; attempt++) {
      try {
        // IMPORTANT: UIv2 scene manager (`magnet/ui_v2/js/scene-manager.js`) expects a URL,
        // not a Blob/ArrayBuffer. So we probe readiness with a lightweight request, then load via URL.
        const url = `${this.baseUrl}/api/v1/designs/${this.designId}/3d/export/glb?v=${version}`;
        const resp = await fetch(url, { cache: 'no-store', method: 'GET' });

        if (resp.ok) {
          if (this._sceneManager && typeof this._sceneManager.loadGLB === 'function') {
            await this._sceneManager.loadGLB(url);
          } else {
            console.warn('[MAGNET] Scene manager missing loadGLB(url); skipping render.');
          }
          this._renderedVersion = version;
          return true;
        }

        if (resp.status === 404 || resp.status === 202) {
          const delay = initialDelayMs * Math.pow(2, attempt);
          console.log(`GLB not ready, retrying in ${delay}ms (attempt ${attempt + 1}/${retryLimit})`);
          await new Promise(r => setTimeout(r, delay));
          continue;
        }

        throw new Error(`GLB fetch failed: ${resp.status}`);
      } catch (e) {
        if (attempt === retryLimit - 1) {
          console.error('GLB load failed after max retries:', e);
          throw e;
        }
      }
    }
    throw new Error('GLB not ready after max retries');
  }

  // ============================================================
  // §SKELETON:WSResync — Resync state after WS reconnection
  // ============================================================
  async onWsReconnect() {
    console.log('WS reconnected, resyncing state...');
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}`);
      if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
      
      const state = await response.json();
      this._lastDesignVersion = state.design_version || 0;
      this._spiralIteration = state.metadata?.spiral_iteration || 0;

      if (state.design_version !== this._renderedVersion) {
        await this._loadHullGeometryWithRetry(state.design_version);
      }

      this._refreshAllPanels(state);
      console.log('State resynced successfully');
    } catch (e) {
      console.error('Resync failed:', e);
      this._showErrorFeedback('Connection restored but state sync failed', ['Please refresh the page']);
    }
  }

  // ============================================================
  // §SKELETON:SketchConfirm — Handle sketch upload with confirmation
  // ============================================================
  async sendSketch(imageFile, annotations = '') {
    if (!this.designId) throw new Error('No design selected');

    this._lastSketchImage = imageFile;
    this._lastSketchAnnotations = annotations;

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('annotations', annotations);
    formData.append('confirm_execution', 'false');

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/sketch`, {
        method: 'POST',
        body: formData
      });

      if (response.status === 409) {
        return this._handleConflict(response, `[sketch: ${annotations}]`);
      }

      if (!response.ok) {
        throw new Error(`Sketch upload failed: ${response.status}`);
      }

      const result = await response.json();
      return this._handleSketchResult(result);
    } catch (e) {
      this._showErrorFeedback('Sketch upload failed', [e.message]);
      throw e;
    }
  }

  async _handleSketchResult(result) {
    if (!result.requires_confirmation) {
      return this._handleSpiralResponse(result);
    }

    const confirmed = await this._showSketchConfirmationDialog({
      extractedValues: result.extracted_values,
      interpretation: result.interpretation,
      intentString: result.intent_string,
      confidence: result.average_confidence
    });

    if (!confirmed) {
      return null;
    }

    const formData = new FormData();
    formData.append('image', this._lastSketchImage);
    formData.append('annotations', this._lastSketchAnnotations);
    formData.append('confirm_execution', 'true');
    formData.append('expected_version', String(this._lastDesignVersion));

    const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/sketch`, {
      method: 'POST',
      body: formData
    });

    return this._handleSpiralResponse(await response.json());
  }

  // ============================================================
  // §SKELETON:PhaseRefresh — Refresh panels from response
  // ============================================================
  _refreshPhasesFromResponse(result) {
    const phases = result.invalidated_phases || ['hull_form', 'weight_stability', 'structure'];
    
    phases.forEach(phase => {
      const panel = this._panels[phase];
      if (panel && typeof panel.refresh === 'function') {
        panel.refresh();
      }
    });

    if (result.metrics) {
      this._updateMetricsPanel(result.metrics, result.deltas);
    }
  }

  _refreshAllPanels(state) {
    Object.values(this._panels).forEach(panel => {
      if (panel && typeof panel.refresh === 'function') {
        panel.refresh(state);
      }
    });
  }

  // ============================================================
  // §SKELETON:SpiralAdapterHelpers — UI Helper Methods
  // ============================================================

  async _showConfirmationDialog({ title, message, details, confirmText = 'Confirm', cancelText = 'Cancel' }) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'spiral-modal-overlay';
      overlay.innerHTML = `
        <div class="spiral-modal">
          <div class="spiral-modal-header">
            <h3>${this._escapeHtml(title)}</h3>
          </div>
          <div class="spiral-modal-body">
            <p>${this._escapeHtml(message)}</p>
            ${details ? `<pre class="spiral-modal-details">${this._escapeHtml(details)}</pre>` : ''}
          </div>
          <div class="spiral-modal-footer">
            <button class="btn btn-secondary spiral-modal-cancel">${this._escapeHtml(cancelText)}</button>
            <button class="btn btn-primary spiral-modal-confirm">${this._escapeHtml(confirmText)}</button>
          </div>
        </div>
      `;

      const cleanup = (result) => {
        overlay.remove();
        resolve(result);
      };

      overlay.querySelector('.spiral-modal-cancel').onclick = () => cleanup(false);
      overlay.querySelector('.spiral-modal-confirm').onclick = () => cleanup(true);
      overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };

      document.body.appendChild(overlay);
      overlay.querySelector('.spiral-modal-confirm').focus();
    });
  }

  async _showSketchConfirmationDialog({ extractedValues, interpretation, intentString, confidence }) {
    const valuesHtml = Object.entries(extractedValues || {})
      .map(([k, v]) => `<tr><td>${this._escapeHtml(k)}</td><td>${this._escapeHtml(String(v))}</td></tr>`)
      .join('');

    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'spiral-modal-overlay';
      overlay.innerHTML = `
        <div class="spiral-modal spiral-modal-wide">
          <div class="spiral-modal-header">
            <h3>📐 Confirm Sketch Interpretation</h3>
            <span class="confidence-badge ${confidence > 0.7 ? 'high' : confidence > 0.4 ? 'medium' : 'low'}">
              ${(confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <div class="spiral-modal-body">
            <div class="sketch-section">
              <h4>Extracted Values</h4>
              <table class="extracted-values-table">
                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                <tbody>${valuesHtml || '<tr><td colspan="2">No values extracted</td></tr>'}</tbody>
              </table>
            </div>
            <div class="sketch-section">
              <h4>Interpreted Intent</h4>
              <p class="intent-string">${this._escapeHtml(intentString || 'No intent extracted')}</p>
            </div>
          </div>
          <div class="spiral-modal-footer">
            <button class="btn btn-secondary spiral-modal-cancel">Cancel</button>
            <button class="btn btn-primary spiral-modal-confirm">Execute Design</button>
          </div>
        </div>
      `;

      const cleanup = (result) => {
        overlay.remove();
        resolve(result);
      };

      overlay.querySelector('.spiral-modal-cancel').onclick = () => cleanup(false);
      overlay.querySelector('.spiral-modal-confirm').onclick = () => cleanup(true);
      overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };

      document.body.appendChild(overlay);
    });
  }

  _showSuccessFeedback(message, metrics, deltas) {
    this._showToast({
      type: 'success',
      title: '✓ Success',
      message,
      details: this._formatMetrics(metrics, deltas),
      duration: 5000
    });
  }

  _showErrorFeedback(message, errors = []) {
    this._showToast({
      type: 'error',
      title: '✗ Error',
      message,
      details: errors.join('\n'),
      duration: 8000
    });
  }

  _showWarningBanner({ message, actions = [] }) {
    this._dismissWarning();

    const banner = document.createElement('div');
    banner.id = 'spiral-warning-banner';
    banner.className = 'spiral-warning-banner';
    banner.innerHTML = `
      <span class="warning-icon">⚠️</span>
      <span class="warning-message">${this._escapeHtml(message)}</span>
      <div class="warning-actions">
        ${actions.map(a => `<button class="btn btn-small">${this._escapeHtml(a.label)}</button>`).join('')}
      </div>
    `;

    const buttons = banner.querySelectorAll('.warning-actions button');
    actions.forEach((action, i) => {
      if (buttons[i]) buttons[i].onclick = action.onClick;
    });

    const container = document.querySelector('.workspace') || document.body;
    container.insertBefore(banner, container.firstChild);
  }

  _dismissWarning() {
    const banner = document.getElementById('spiral-warning-banner');
    if (banner) banner.remove();
  }

  _showPhaseErrors(failedPhases) {
    this._showConfirmationDialog({
      title: 'Phase Errors',
      message: 'The following phases failed during execution:',
      details: failedPhases.map(p => `• ${p}`).join('\n'),
      confirmText: 'OK',
      cancelText: 'Close'
    });
  }

  _updateMetricsPanel(metrics, deltas) {
    const panel = document.getElementById('metrics-panel');
    if (!panel) return;

    const rows = Object.entries(metrics).map(([key, value]) => {
      const delta = deltas?.[key];
      const deltaClass = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
      const deltaStr = delta ? ` (${delta > 0 ? '+' : ''}${delta.toFixed(2)})` : '';
      return `
        <tr>
          <td>${this._escapeHtml(key)}</td>
          <td>${typeof value === 'number' ? value.toFixed(3) : value}</td>
          <td class="delta ${deltaClass}">${deltaStr}</td>
        </tr>
      `;
    }).join('');

    panel.innerHTML = `
      <table class="metrics-table">
        <thead><tr><th>Metric</th><th>Value</th><th>Change</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  _showToast({ type, title, message, details, duration = 5000 }) {
    let container = document.getElementById('spiral-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'spiral-toast-container';
      container.className = 'spiral-toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `spiral-toast spiral-toast-${type}`;
    toast.innerHTML = `
      <div class="toast-header">
        <strong>${this._escapeHtml(title)}</strong>
        <button class="toast-close">×</button>
      </div>
      <div class="toast-body">
        <p>${this._escapeHtml(message)}</p>
        ${details ? `<pre class="toast-details">${this._escapeHtml(details)}</pre>` : ''}
      </div>
    `;

    toast.querySelector('.toast-close').onclick = () => toast.remove();
    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => toast.remove(), duration);
    }
  }

  _formatMetrics(metrics, deltas) {
    if (!metrics || Object.keys(metrics).length === 0) return '';
    return Object.entries(metrics)
      .map(([k, v]) => {
        const d = deltas?.[k];
        const dStr = d ? ` (${d > 0 ? '+' : ''}${d.toFixed(2)})` : '';
        return `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}${dStr}`;
      })
      .join('\n');
  }

  _escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Export to global scope for UIv2 (non-module)
window.SpiralAdapter = SpiralAdapter;
window.ClarificationPanel = ClarificationPanel;

