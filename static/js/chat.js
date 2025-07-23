// Chat functionality for Shutter Synth
class ChatInterface {
    constructor() {
        this.chatContainer = document.getElementById('chatContainer');
        this.messageForm = document.getElementById('messageForm');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.sessionToken = document.getElementById('sessionToken').value;
        this.typingIndicator = document.getElementById('typingIndicator');
        this.imageInput = document.getElementById('imageInput');
        this.imageUploadArea = document.getElementById('imageUploadArea');
        this.imagePreview = document.getElementById('imagePreview');
        this.selectedFiles = [];
        
        this.initializeEventListeners();
        this.scrollToBottom();
    }
    
    initializeEventListeners() {
        // Message form submission
        this.messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Enter key handling (Shift+Enter for new line, Enter to send)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Quick reply buttons
        document.querySelectorAll('.quick-reply').forEach(button => {
            button.addEventListener('click', (e) => {
                const message = e.target.dataset.message;
                this.messageInput.value = message;
                this.sendMessage();
            });
        });
        
        // Quick style buttons
        document.querySelectorAll('.quick-style').forEach(button => {
            button.addEventListener('click', (e) => {
                const style = e.target.dataset.style;
                this.messageInput.value = `I want to create a ${style}`;
                this.sendMessage();
            });
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        // Image upload event listeners
        this.imageInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });
        
        // Drag and drop for image upload area
        this.imageUploadArea.addEventListener('click', () => {
            this.imageInput.click();
        });
        
        this.imageUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.add('dragover');
        });
        
        this.imageUploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.remove('dragover');
        });
        
        this.imageUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.imageUploadArea.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files);
        });
    }
    
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = (this.messageInput.scrollHeight) + 'px';
    }
    
    handleFileSelect(files) {
        // Add selected files to the array
        for (let file of files) {
            if (this.isValidImageFile(file)) {
                this.selectedFiles.push(file);
                this.addImagePreview(file);
            } else {
                alert(`${file.name} is not a valid image file. Please select PNG, JPG, GIF, or other image formats.`);
            }
        }
    }
    
    isValidImageFile(file) {
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        
        if (!validTypes.includes(file.type)) {
            return false;
        }
        
        if (file.size > maxSize) {
            alert(`${file.name} is too large. Maximum file size is 16MB.`);
            return false;
        }
        
        return true;
    }
    
    addImagePreview(file) {
        const previewItem = document.createElement('div');
        previewItem.className = 'image-preview-item';
        
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.alt = file.name;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-image';
        removeBtn.innerHTML = '×';
        removeBtn.onclick = () => {
            this.removeImagePreview(file, previewItem);
        };
        
        previewItem.appendChild(img);
        previewItem.appendChild(removeBtn);
        this.imagePreview.appendChild(previewItem);
    }
    
    removeImagePreview(file, previewItem) {
        // Remove from selected files
        this.selectedFiles = this.selectedFiles.filter(f => f !== file);
        
        // Remove preview element
        previewItem.remove();
        
        // Revoke object URL to free memory
        URL.revokeObjectURL(previewItem.querySelector('img').src);
    }
    
    clearImagePreviews() {
        // Revoke all object URLs
        this.imagePreview.querySelectorAll('img').forEach(img => {
            URL.revokeObjectURL(img.src);
        });
        
        // Clear preview container and selected files
        this.imagePreview.innerHTML = '';
        this.selectedFiles = [];
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        // Check if we have message or images
        if (!message && this.selectedFiles.length === 0) {
            return;
        }
        
        // Disable input while sending
        this.setLoadingState(true);
        
        // Prepare message content for display
        let displayMessage = message || 'Uploaded image for analysis';
        if (this.selectedFiles.length > 0) {
            displayMessage += ` [${this.selectedFiles.length} image(s) attached]`;
        }
        
        // Add user message to chat
        this.addMessage('user', displayMessage);
        
        // Clear input
        this.messageInput.value = '';
        this.autoResizeTextarea();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            let response;
            
            if (this.selectedFiles.length > 0) {
                // Send as FormData for file uploads
                const formData = new FormData();
                formData.append('message', message);
                formData.append('session_token', this.sessionToken);
                
                // Add all selected files
                this.selectedFiles.forEach((file, index) => {
                    formData.append('images', file);
                });
                
                response = await fetch('/chat/send', {
                    method: 'POST',
                    body: formData
                });
                
                // Clear uploaded images after sending
                this.clearImagePreviews();
            } else {
                // Send as JSON for text-only messages
                response = await fetch('/chat/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_token: this.sessionToken
                    })
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add bot response
            this.addMessage('bot', data.response, data.step_number);
            
            // Update UI based on response type
            if (data.awaiting_continuation) {
                this.highlightQuickReplies();
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            
            // Show error message
            this.addMessage('bot', 'Sorry, I encountered an error while processing your request. Please try again.', null, true);
        } finally {
            this.setLoadingState(false);
        }
    }
    
    addMessage(type, content, stepNumber = null, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        // Create timestamp
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Create message header
        let headerContent = '';
        if (type === 'user') {
            headerContent = '<i class="fas fa-user"></i> You';
        } else {
            headerContent = '<i class="fas fa-robot"></i> Synthia';
            if (stepNumber) {
                headerContent += ` <span class="badge bg-info ms-2">Step ${stepNumber}</span>`;
            }
            if (isError) {
                headerContent += ` <span class="badge bg-danger ms-2">Error</span>`;
            }
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">
                ${headerContent}
                <small class="text-muted ms-2">${timeString}</small>
            </div>
            <div class="message-content">${this.formatMessageContent(content)}</div>
        `;
        
        // Insert before typing indicator
        this.chatContainer.insertBefore(messageDiv, this.typingIndicator);
        
        // Animate message appearance
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(10px)';
        
        requestAnimationFrame(() => {
            messageDiv.style.transition = 'all 0.3s ease-out';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        });
        
        this.scrollToBottom();
    }
    
    formatMessageContent(content) {
        // Convert markdown-style formatting to HTML
        let formatted = content
            // Bold text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Headers
            .replace(/^### (.*$)/gm, '<h6>$1</h6>')
            .replace(/^## (.*$)/gm, '<h5>$1</h5>')
            .replace(/^# (.*$)/gm, '<h4>$1</h4>')
            // Lists
            .replace(/^- (.*$)/gm, '<li>$1</li>')
            .replace(/^• (.*$)/gm, '<li>$1</li>')
            // Step indicators
            .replace(/🟦/g, '<span class="badge bg-info">🔵</span>')
            .replace(/📌/g, '<span class="text-warning">📌</span>')
            .replace(/⚠️/g, '<span class="text-danger">⚠️</span>');
        
        // Wrap consecutive list items in ul tags
        formatted = formatted.replace(/(<li>.*<\/li>\s*)+/g, '<ul class="list-unstyled ms-3">$&</ul>');
        
        // Convert newlines to breaks, but preserve paragraph structure
        formatted = formatted.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        formatted = '<p>' + formatted + '</p>';
        
        // Clean up empty paragraphs
        formatted = formatted.replace(/<p><\/p>/g, '').replace(/<p><br><\/p>/g, '');
        
        return formatted;
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    highlightQuickReplies() {
        // Temporarily highlight quick reply buttons
        const quickReplies = document.querySelectorAll('.quick-reply');
        quickReplies.forEach(button => {
            button.classList.add('btn-outline-success');
            button.classList.remove('btn-outline-secondary');
            
            // Reset after 3 seconds
            setTimeout(() => {
                button.classList.remove('btn-outline-success');
                button.classList.add('btn-outline-secondary');
            }, 3000);
        });
    }
    
    setLoadingState(loading) {
        if (loading) {
            this.sendButton.disabled = true;
            this.messageInput.disabled = true;
            this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        } else {
            this.sendButton.disabled = false;
            this.messageInput.disabled = false;
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
            this.messageInput.focus();
        }
    }
    
    scrollToBottom() {
        // Smooth scroll to bottom with a slight delay for animations
        setTimeout(() => {
            this.chatContainer.scrollTo({
                top: this.chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }
}

// Enhanced message formatting
class MessageFormatter {
    static formatPhotographyContent(content) {
        // Special formatting for photography-specific content
        return content
            // Camera settings
            .replace(/f\/(\d+\.?\d*)/g, '<code class="bg-secondary px-1 rounded">f/$1</code>')
            .replace(/(\d+)mm/g, '<code class="bg-secondary px-1 rounded">$1mm</code>')
            .replace(/ISO\s*(\d+)/gi, '<code class="bg-secondary px-1 rounded">ISO $1</code>')
            .replace(/1\/(\d+)s/g, '<code class="bg-secondary px-1 rounded">1/$1s</code>')
            // Equipment mentions
            .replace(/\b([A-Z][a-z]+\s+[A-Z0-9][A-Za-z0-9\s]+)\b/g, '<em>$1</em>')
            // Step headers
            .replace(/Step\s+(\d+):/gi, '<span class="fw-bold text-primary">Step $1:</span>');
    }
}

// Utility functions
function initializeChat() {
    // Initialize chat interface when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new ChatInterface();
        });
    } else {
        new ChatInterface();
    }
}

// Auto-save draft messages
class DraftManager {
    constructor() {
        this.storageKey = 'shuttersynth_draft';
        this.messageInput = document.getElementById('messageInput');
        this.loadDraft();
        this.setupAutoSave();
    }
    
    loadDraft() {
        if (this.messageInput) {
            const draft = localStorage.getItem(this.storageKey);
            if (draft && draft.trim()) {
                this.messageInput.value = draft;
            }
        }
    }
    
    setupAutoSave() {
        if (this.messageInput) {
            this.messageInput.addEventListener('input', () => {
                this.saveDraft();
            });
            
            // Clear draft when message is sent
            document.getElementById('messageForm')?.addEventListener('submit', () => {
                this.clearDraft();
            });
        }
    }
    
    saveDraft() {
        if (this.messageInput?.value.trim()) {
            localStorage.setItem(this.storageKey, this.messageInput.value);
        } else {
            this.clearDraft();
        }
    }
    
    clearDraft() {
        localStorage.removeItem(this.storageKey);
    }
}

// Keyboard shortcuts
class KeyboardShortcuts {
    constructor() {
        this.setupShortcuts();
    }
    
    setupShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to send message
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                const messageForm = document.getElementById('messageForm');
                if (messageForm) {
                    messageForm.dispatchEvent(new Event('submit'));
                }
            }
            
            // Escape to clear input
            if (e.key === 'Escape') {
                const messageInput = document.getElementById('messageInput');
                if (messageInput && document.activeElement === messageInput) {
                    messageInput.value = '';
                    messageInput.blur();
                }
            }
            
            // Focus input with '/' key
            if (e.key === '/' && document.activeElement !== document.getElementById('messageInput')) {
                e.preventDefault();
                document.getElementById('messageInput')?.focus();
            }
        });
    }
}

// Initialize everything
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize chat features on chat page
    if (document.getElementById('chatContainer')) {
        new ChatInterface();
        new DraftManager();
        new KeyboardShortcuts();
    }
});

// Export for potential external use
window.ShutterSynth = {
    ChatInterface,
    MessageFormatter,
    DraftManager,
    KeyboardShortcuts
};
