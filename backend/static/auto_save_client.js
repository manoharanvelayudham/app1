/**
 * Auto-Save Client Implementation
 * Automatically saves form data every 30 seconds
 * Handles offline detection and retry logic
 */

class AutoSaveClient {
    constructor(options = {}) {
        this.responseId = options.responseId;
        this.apiEndpoint = options.apiEndpoint || '/responses';
        this.saveInterval = options.saveInterval || 30000; // 30 seconds
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 5000; // 5 seconds
        
        // State management
        this.isEnabled = options.autoSave !== false;
        this.isDirty = false;
        this.isSaving = false;
        this.isOnline = navigator.onLine;
        this.lastSaveTime = null;
        this.saveTimer = null;
        this.retryCount = 0;
        this.pendingData = null;
        
        // Callbacks
        this.onSaveSuccess = options.onSaveSuccess || this.defaultOnSaveSuccess;
        this.onSaveError = options.onSaveError || this.defaultOnSaveError;
        this.onOffline = options.onOffline || this.defaultOnOffline;
        this.onOnline = options.onOnline || this.defaultOnOnline;
        
        // Event listeners
        this.setupEventListeners();
        
        // Start auto-save if enabled
        if (this.isEnabled && this.responseId) {
            this.start();
        }
    }
    
    setupEventListeners() {
        // Online/offline detection
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.onOnline();
            if (this.pendingData) {
                this.performSave(this.pendingData);
            }
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.onOffline();
        });
        
        // Page unload - attempt final save
        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty && !this.isSaving) {
                // Try synchronous save on page unload
                this.performSyncSave();
            }
        });
        
        // Visibility change - save when tab becomes hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isDirty && !this.isSaving) {
                this.save();
            }
        });
    }
    
    start() {
        if (!this.isEnabled || this.saveTimer) return;
        
        this.saveTimer = setInterval(() => {
            if (this.isDirty && !this.isSaving) {
                this.save();
            }
        }, this.saveInterval);
        
        console.log('Auto-save started with interval:', this.saveInterval);
    }
    
    stop() {
        if (this.saveTimer) {
            clearInterval(this.saveTimer);
            this.saveTimer = null;
        }
        console.log('Auto-save stopped');
    }
    
    enable() {
        this.isEnabled = true;
        this.start();
    }
    
    disable() {
        this.isEnabled = false;
        this.stop();
    }
    
    markDirty(data = null) {
        this.isDirty = true;
        if (data) {
            this.pendingData = data;
        }
        
        // Show dirty indicator
        this.updateUI('dirty');
    }
    
    markClean() {
        this.isDirty = false;
        this.pendingData = null;
        this.retryCount = 0;
        this.lastSaveTime = new Date();
        
        // Update UI
        this.updateUI('clean');
    }
    
    async save(data = null) {
        if (!this.isEnabled || this.isSaving) return;
        
        const saveData = data || this.pendingData || this.collectFormData();
        
        if (!saveData || Object.keys(saveData).length === 0) {
            console.log('No data to save');
            return;
        }
        
        if (!this.isOnline) {
            console.log('Offline - saving data for later');
            this.pendingData = saveData;
            this.updateUI('offline');
            return;
        }
        
        await this.performSave(saveData);
    }
    
    async performSave(data) {
        if (this.isSaving) return;
        
        this.isSaving = true;
        this.updateUI('saving');
        
        try {
            const response = await fetch(`${this.apiEndpoint}/${this.responseId}/autosave`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    response_content: data,
                    metadata: {
                        timestamp: new Date().toISOString(),
                        user_agent: navigator.userAgent,
                        auto_save_trigger: 'periodic'
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`Save failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Success
            this.markClean();
            this.onSaveSuccess(result);
            
            console.log('Auto-save successful:', result);
            
        } catch (error) {
            console.error('Auto-save failed:', error);
            
            // Retry logic
            if (this.retryCount < this.maxRetries) {
                this.retryCount++;
                console.log(`Retrying save (${this.retryCount}/${this.maxRetries})`);
                
                setTimeout(() => {
                    this.performSave(data);
                }, this.retryDelay);
                
                this.updateUI('retrying');
            } else {
                // Max retries exceeded
                this.onSaveError(error);
                this.updateUI('error');
                this.retryCount = 0;
            }
        } finally {
            this.isSaving = false;
        }
    }
    
    performSyncSave() {
        // Synchronous save for page unload (limited browser support)
        if (!this.pendingData || !this.isOnline) return;
        
        try {
            const beacon = navigator.sendBeacon(
                `${this.apiEndpoint}/${this.responseId}/autosave`,
                new Blob([JSON.stringify({
                    response_content: this.pendingData,
                    metadata: {
                        timestamp: new Date().toISOString(),
                        auto_save_trigger: 'page_unload'
                    }
                })], { type: 'application/json' })
            );
            
            if (beacon) {
                console.log('Emergency save sent via beacon');
            }
        } catch (error) {
            console.error('Emergency save failed:', error);
        }
    }
    
    collectFormData() {
        // Override this method to collect data from your specific form
        const formData = {};
        
        // Example: collect from form with data-autosave attributes
        document.querySelectorAll('[data-autosave]').forEach(element => {
            const key = element.getAttribute('data-autosave') || element.name || element.id;
            
            if (element.type === 'checkbox') {
                formData[key] = element.checked;
            } else if (element.type === 'radio') {
                if (element.checked) {
                    formData[key] = element.value;
                }
            } else {
                formData[key] = element.value;
            }
        });
        
        // Collect from rich text editors (TinyMCE, Quill, etc.)
        if (window.tinymce) {
            window.tinymce.editors.forEach(editor => {
                if (editor.id) {
                    formData[editor.id] = editor.getContent();
                }
            });
        }
        
        return formData;
    }
    
    updateUI(status) {
        // Update auto-save status indicator
        const indicator = document.querySelector('.autosave-status');
        if (!indicator) return;
        
        const messages = {
            'clean': { text: 'All changes saved', class: 'saved' },
            'dirty': { text: 'Unsaved changes', class: 'dirty' },
            'saving': { text: 'Saving...', class: 'saving' },
            'retrying': { text: 'Retrying save...', class: 'retrying' },
            'offline': { text: 'Offline - will save when online', class: 'offline' },
            'error': { text: 'Save failed', class: 'error' }
        };
        
        const config = messages[status] || messages['dirty'];
        
        indicator.textContent = config.text;
        indicator.className = `autosave-status ${config.class}`;
        
        // Show timestamp if saved
        if (status === 'clean' && this.lastSaveTime) {
            indicator.textContent += ` at ${this.lastSaveTime.toLocaleTimeString()}`;
        }
    }
    
    getAuthToken() {
        // Get authentication token - adjust for your auth system
        return localStorage.getItem('auth_token') || 
               sessionStorage.getItem('auth_token') ||
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }
    
    // Default event handlers
    defaultOnSaveSuccess(result) {
        console.log('Auto-save successful:', result);
        
        // Update version info if available
        if (result.version) {
            document.querySelector('[data-version]')?.setAttribute('data-version', result.version);
        }
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('autosave:success', {
            detail: result
        }));
    }
    
    defaultOnSaveError(error) {
        console.error('Auto-save error:', error);
        
        // Show user-friendly error message
        this.showNotification('Failed to save changes automatically. Your work may be lost.', 'error');
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('autosave:error', {
            detail: error
        }));
    }
    
    defaultOnOffline() {
        console.log('Gone offline - auto-save paused');
        this.showNotification('You are offline. Changes will be saved when connection is restored.', 'warning');
    }
    
    defaultOnOnline() {
        console.log('Back online - resuming auto-save');
        this.showNotification('Connection restored. Auto-save resumed.', 'success');
    }
    
    showNotification(message, type = 'info') {
        // Simple notification system - replace with your preferred notification library
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '4px',
            zIndex: '10000',
            color: 'white',
            fontSize: '14px',
            maxWidth: '300px',
            backgroundColor: type === 'error' ? '#dc3545' : 
                           type === 'warning' ? '#ffc107' : 
                           type === 'success' ? '#28a745' : '#17a2b8'
        });
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // Manual save trigger
    async forceSave() {
        const data = this.collectFormData();
        if (data && Object.keys(data).length > 0) {
            this.markDirty(data);
            await this.save();
        }
    }
    
    // Get save status
    getSaveStatus() {
        return {
            isEnabled: this.isEnabled,
            isDirty: this.isDirty,
            isSaving: this.isSaving,
            isOnline: this.isOnline,
            lastSaveTime: this.lastSaveTime,
            retryCount: this.retryCount,
            hasPendingData: !!this.pendingData
        };
    }
    
    // Destroy instance
    destroy() {
        this.stop();
        
        // Remove event listeners
        window.removeEventListener('online', this.onOnline);
        window.removeEventListener('offline', this.onOffline);
        window.removeEventListener('beforeunload', this.performSyncSave);
        document.removeEventListener('visibilitychange', this.save);
        
        // Clear data
        this.pendingData = null;
        this.responseId = null;
    }
}

// Form integration helper
class AutoSaveFormIntegration {
    constructor(formSelector, autoSaveOptions = {}) {
        this.form = document.querySelector(formSelector);
        this.autoSave = null;
        
        if (!this.form) {
            console.error('Form not found:', formSelector);
            return;
        }
        
        // Initialize auto-save
        this.autoSave = new AutoSaveClient({
            ...autoSaveOptions,
            responseId: this.form.dataset.responseId || autoSaveOptions.responseId
        });
        
        this.setupFormListeners();
    }
    
    setupFormListeners() {
        // Listen for form changes
        this.form.addEventListener('input', (e) => {
            this.autoSave.markDirty();
        });
        
        this.form.addEventListener('change', (e) => {
            this.autoSave.markDirty();
        });
        
        // Manual save button
        const saveButton = this.form.querySelector('[data-manual-save]');
        if (saveButton) {
            saveButton.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.autoSave.forceSave();
            });
        }
        
        // Form submission - ensure final save
        this.form.addEventListener('submit', async (e) => {
            if (this.autoSave.isDirty) {
                e.preventDefault();
                
                try {
                    await this.autoSave.forceSave();
                    // Re-submit form after save
                    setTimeout(() => this.form.submit(), 100);
                } catch (error) {
                    console.error('Pre-submit save failed:', error);
                    // Allow form submission anyway
                    this.form.submit();
                }
            }
        });
    }
    
    getAutoSave() {
        return this.autoSave;
    }
}

// Usage Examples and initialization
document.addEventListener('DOMContentLoaded', function() {
    // Example 1: Simple auto-save setup
    if (document.querySelector('#response-form')) {
        window.autoSaveIntegration = new AutoSaveFormIntegration('#response-form', {
            saveInterval: 30000, // 30 seconds
            onSaveSuccess: (result) => {
                console.log('Save successful:', result);
                document.querySelector('#last-saved').textContent = 
                    `Last saved: ${new Date().toLocaleTimeString()}`;
            }
        });
    }
    
    // Example 2: Advanced setup with custom data collection
    if (document.querySelector('#advanced-form')) {
        const autoSave = new AutoSaveClient({
            responseId: document.querySelector('#advanced-form').dataset.responseId,
            saveInterval: 15000, // 15 seconds for faster saving
            onSaveError: (error) => {
                // Custom error handling
                document.querySelector('#error-message').textContent = 
                    'Auto-save failed. Please save manually.';
            }
        });
        
        // Custom data collection
        autoSave.collectFormData = function() {
            const data = {};
            
            // Collect from specific elements
            data.title = document.querySelector('#title').value;
            data.content = document.querySelector('#content').value;
            
            // Collect from rich text editor
            if (window.quill) {
                data.rich_content = window.quill.getContents();
            }
            
            return data;
        };
        
        // Mark form as dirty when user types
        document.querySelectorAll('#advanced-form input, #advanced-form textarea').forEach(el => {
            el.addEventListener('input', () => autoSave.markDirty());
        });
        
        window.advancedAutoSave = autoSave;
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AutoSaveClient, AutoSaveFormIntegration };
}

// Global access
window.AutoSaveClient = AutoSaveClient;
window.AutoSaveFormIntegration = AutoSaveFormIntegration;