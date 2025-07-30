/**
 * Source-to-Sell Extension Background Script
 * Handles extension lifecycle and cross-tab communication
 */

// Extension installation/update handler
chrome.runtime.onInstalled.addListener((details) => {
    console.log('Source-to-Sell extension installed/updated:', details);
    
    // Set up default settings
    chrome.storage.local.set({
        apiBase: 'http://localhost:8000',
        extensionVersion: chrome.runtime.getManifest().version
    });
});

// Handle extension icon click
chrome.action.onClicked.addListener((tab) => {
    // This will open the popup (default behavior)
    // Additional logic can be added here if needed
    console.log('Extension icon clicked for tab:', tab.url);
});

// Message passing between content scripts and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Background received message:', request);
    
    switch (request.action) {
        case 'getTabInfo':
            if (sender.tab) {
                sendResponse({
                    tabId: sender.tab.id,
                    url: sender.tab.url,
                    title: sender.tab.title
                });
            }
            break;
            
        case 'openAccountPage':
            if (request.accountId) {
                const url = `http://localhost:8000/accounts/${request.accountId}/view`;
                chrome.tabs.create({ url });
            }
            break;
            
        case 'showNotification':
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: 'Source-to-Sell',
                message: request.message
            });
            break;
            
        default:
            console.log('Unknown action:', request.action);
    }
    
    return true; // Keep message channel open for async response
});

// Context menu integration (optional)
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: 'capture-prospect',
        title: 'Capture as Prospect',
        contexts: ['page']
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'capture-prospect') {
        // Open popup programmatically
        chrome.action.openPopup();
    }
});

// Handle API errors and retry logic
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'apiRequest') {
        handleApiRequest(request)
            .then(response => sendResponse({ success: true, data: response }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        
        return true; // Async response
    }
});

async function handleApiRequest(request) {
    const { endpoint, method = 'GET', data } = request;
    const apiBase = 'http://localhost:8000';
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${apiBase}${endpoint}`, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}