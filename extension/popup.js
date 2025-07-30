/**
 * Source-to-Sell Extension Popup
 * Handles prospect capture and API communication
 */

// API configuration
const API_BASE = 'http://localhost:8000';

// DOM elements
let extraUrlCount = 0;
const maxExtraUrls = 2;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentPageData();
    setupEventListeners();
    await loadStoredData();
});

/**
 * Load data from current active tab
 */
async function loadCurrentPageData() {
    try {
        // Get current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab || !tab.url || tab.url.startsWith('chrome://')) {
            return;
        }
        
        // Inject content script to detect company info
        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            function: detectCompanyInfo
        });
        
        if (results && results[0] && results[0].result) {
            const companyInfo = results[0].result;
            displayDetectedInfo(companyInfo);
            populateForm(companyInfo);
        }
    } catch (error) {
        console.error('Error loading page data:', error);
    }
}

/**
 * Content script function to detect company information
 * This runs in the context of the current page
 */
function detectCompanyInfo() {
    const url = window.location.href;
    const domain = window.location.hostname.replace(/^www\./, '');
    
    // Try to detect company name from various sources
    let companyName = '';
    
    // Method 1: Page title
    const title = document.title;
    if (title) {
        // Remove common suffixes
        companyName = title
            .replace(/\s*[-|–]\s*(Home|Homepage|Welcome|About|Official Site).*$/i, '')
            .replace(/\s*\|\s*.*$/, '')
            .trim();
    }
    
    // Method 2: Meta tags
    if (!companyName) {
        const metaTags = ['og:site_name', 'twitter:site', 'application-name'];
        for (const metaName of metaTags) {
            const meta = document.querySelector(`meta[property="${metaName}"], meta[name="${metaName}"]`);
            if (meta && meta.content) {
                companyName = meta.content.replace(/^@/, '');
                break;
            }
        }
    }
    
    // Method 3: Schema.org Organization
    if (!companyName) {
        const orgScript = document.querySelector('script[type="application/ld+json"]');
        if (orgScript) {
            try {
                const data = JSON.parse(orgScript.textContent);
                if (data.name && (data['@type'] === 'Organization' || data['@type'] === 'Corporation')) {
                    companyName = data.name;
                }
            } catch (e) {
                // Ignore JSON parse errors
            }
        }
    }
    
    // Method 4: Common patterns in title/domain
    if (!companyName) {
        // Extract from domain (remove TLD)
        companyName = domain.split('.')[0];
        // Capitalize first letter
        companyName = companyName.charAt(0).toUpperCase() + companyName.slice(1);
    }
    
    return {
        name: companyName,
        domain: domain,
        url: url,
        title: title
    };
}

/**
 * Display detected company information
 */
function displayDetectedInfo(companyInfo) {
    const detectedInfo = document.getElementById('detectedInfo');
    const detectedName = document.getElementById('detectedName');
    const detectedDomain = document.getElementById('detectedDomain');
    
    detectedName.textContent = `📊 ${companyInfo.name}`;
    detectedDomain.textContent = `🌐 ${companyInfo.domain}`;
    detectedInfo.style.display = 'block';
}

/**
 * Populate form with detected data
 */
function populateForm(companyInfo) {
    document.getElementById('companyName').value = companyInfo.name;
    document.getElementById('companyUrl').value = companyInfo.url;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Form submission
    document.getElementById('prospectForm').addEventListener('submit', handleFormSubmit);
    
    // Add URL button
    document.getElementById('addUrlBtn').addEventListener('click', addExtraUrlField);
}

/**
 * Add extra URL input field
 */
function addExtraUrlField() {
    if (extraUrlCount >= maxExtraUrls) return;
    
    extraUrlCount++;
    
    const extraUrlsContainer = document.getElementById('extraUrls');
    const urlGroup = document.createElement('div');
    urlGroup.className = 'url-group';
    urlGroup.innerHTML = `
        <input type="url" name="extraUrl${extraUrlCount}" placeholder="https://additional-url.com">
        <button type="button" onclick="removeUrlField(this)" style="float: right; background: none; border: none; color: #e53e3e; cursor: pointer;">×</button>
    `;
    
    extraUrlsContainer.appendChild(urlGroup);
    
    // Hide add button if max reached
    if (extraUrlCount >= maxExtraUrls) {
        document.getElementById('addUrlBtn').style.display = 'none';
    }
}

/**
 * Remove extra URL field
 */
function removeUrlField(button) {
    button.parentElement.remove();
    extraUrlCount--;
    
    // Show add button again
    document.getElementById('addUrlBtn').style.display = 'block';
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const submitBtn = document.getElementById('submitBtn');
    const statusDiv = document.getElementById('status');
    
    // Disable submit button and show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner"></span>Creating Prospect...';
    
    try {
        // Collect form data
        const formData = {
            company_name: document.getElementById('companyName').value.trim(),
            company_url: document.getElementById('companyUrl').value.trim(),
            extra_urls: []
        };
        
        // Collect extra URLs
        const extraUrlInputs = document.querySelectorAll('[name^="extraUrl"]');
        extraUrlInputs.forEach(input => {
            if (input.value.trim()) {
                formData.extra_urls.push(input.value.trim());
            }
        });
        
        // Validate form
        if (!formData.company_name) {
            throw new Error('Company name is required');
        }
        
        if (!formData.company_url) {
            throw new Error('Company URL is required');
        }
        
        // Make API request
        const response = await fetch(`${API_BASE}/prospects/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        // Store account ID for future reference
        await chrome.storage.local.set({
            lastAccountId: result.account_id,
            lastAccountName: formData.company_name
        });
        
        // Show success message
        showStatus('success', 
            `✅ Success! Created prospect for ${formData.company_name}. ` +
            `Fetched ${result.sources_fetched} sources in ${result.processing_time.toFixed(1)}s.`,
            result.account_id
        );
        
        // Reset form
        document.getElementById('prospectForm').reset();
        extraUrlCount = 0;
        document.getElementById('extraUrls').innerHTML = '';
        document.getElementById('addUrlBtn').style.display = 'block';
        
    } catch (error) {
        console.error('Error creating prospect:', error);
        showStatus('error', `❌ Error: ${error.message}`);
    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Prospect';
    }
}

/**
 * Show status message
 */
function showStatus(type, message, accountId = null) {
    const statusDiv = document.getElementById('status');
    statusDiv.className = `status ${type}`;
    statusDiv.innerHTML = message;
    
    if (accountId && type === 'success') {
        statusDiv.innerHTML += `
            <a href="${API_BASE}/accounts/${accountId}/view" target="_blank" class="view-account-btn">
                View Account Details
            </a>
        `;
    }
    
    statusDiv.style.display = 'block';
    
    // Auto-hide success messages after 10 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 10000);
    }
}

/**
 * Load stored data from previous sessions
 */
async function loadStoredData() {
    try {
        const data = await chrome.storage.local.get(['lastAccountId', 'lastAccountName']);
        
        if (data.lastAccountId && data.lastAccountName) {
            showStatus('success', 
                `💡 Last created: ${data.lastAccountName}`,
                data.lastAccountId
            );
        }
    } catch (error) {
        console.error('Error loading stored data:', error);
    }
}

// Global function for removing URL fields (needed for inline onclick)
window.removeUrlField = removeUrlField;