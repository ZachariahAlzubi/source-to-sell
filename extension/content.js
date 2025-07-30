/**
 * Source-to-Sell Content Script
 * Runs on web pages to detect company information
 */

(function() {
    'use strict';
    
    // Avoid running multiple times
    if (window.sourceToSellInjected) {
        return;
    }
    window.sourceToSellInjected = true;
    
    /**
     * Enhanced company detection function
     * Analyzes the current page for company information
     */
    function detectCompanyInformation() {
        const url = window.location.href;
        const domain = window.location.hostname.replace(/^www\./, '');
        
        const companyInfo = {
            name: '',
            domain: domain,
            url: url,
            title: document.title,
            industry: '',
            description: '',
            social: {}
        };
        
        // Method 1: Page title analysis
        let title = document.title;
        if (title) {
            // Clean up common patterns
            companyInfo.name = title
                .replace(/\s*[-|–]\s*(Home|Homepage|Welcome|About|Official Site|Landing Page).*$/i, '')
                .replace(/\s*\|\s*.*$/, '')
                .replace(/\s*-\s*.*$/, '')
                .trim();
        }
        
        // Method 2: Meta tags
        const metaTags = [
            'og:site_name',
            'twitter:site', 
            'application-name',
            'og:title',
            'twitter:title'
        ];
        
        for (const metaName of metaTags) {
            const meta = document.querySelector(`meta[property="${metaName}"], meta[name="${metaName}"]`);
            if (meta && meta.content && !companyInfo.name) {
                companyInfo.name = meta.content.replace(/^@/, '').trim();
                break;
            }
        }
        
        // Method 3: Description from meta tags
        const descMeta = document.querySelector('meta[name="description"], meta[property="og:description"]');
        if (descMeta) {
            companyInfo.description = descMeta.content.trim();
        }
        
        // Method 4: Schema.org structured data
        const ldJsonScripts = document.querySelectorAll('script[type="application/ld+json"]');
        ldJsonScripts.forEach(script => {
            try {
                const data = JSON.parse(script.textContent);
                const processSchemaData = (obj) => {
                    if (obj && typeof obj === 'object') {
                        if (obj['@type'] === 'Organization' || obj['@type'] === 'Corporation') {
                            if (obj.name && !companyInfo.name) {
                                companyInfo.name = obj.name;
                            }
                            if (obj.description && !companyInfo.description) {
                                companyInfo.description = obj.description;
                            }
                        }
                        
                        // Recursively check nested objects
                        Object.values(obj).forEach(value => {
                            if (Array.isArray(value)) {
                                value.forEach(processSchemaData);
                            } else if (typeof value === 'object') {
                                processSchemaData(value);
                            }
                        });
                    }
                };
                
                if (Array.isArray(data)) {
                    data.forEach(processSchemaData);
                } else {
                    processSchemaData(data);
                }
            } catch (e) {
                // Ignore JSON parse errors
            }
        });
        
        // Method 5: Common DOM selectors for company names
        if (!companyInfo.name) {
            const selectors = [
                '.company-name',
                '.brand-name', 
                '.logo-text',
                'h1.site-title',
                '.site-title h1',
                'header h1',
                '.navbar-brand'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.textContent.trim()) {
                    companyInfo.name = element.textContent.trim();
                    break;
                }
            }
        }
        
        // Method 6: Social media links
        const socialLinks = document.querySelectorAll('a[href*="twitter.com"], a[href*="linkedin.com"], a[href*="facebook.com"]');
        socialLinks.forEach(link => {
            const href = link.href;
            if (href.includes('twitter.com')) {
                companyInfo.social.twitter = href;
            } else if (href.includes('linkedin.com')) {
                companyInfo.social.linkedin = href;
            } else if (href.includes('facebook.com')) {
                companyInfo.social.facebook = href;
            }
        });
        
        // Method 7: Fallback to domain name
        if (!companyInfo.name) {
            companyInfo.name = domain.split('.')[0];
            companyInfo.name = companyInfo.name.charAt(0).toUpperCase() + companyInfo.name.slice(1);
        }
        
        // Method 8: Try to detect industry from keywords
        const content = document.body.textContent.toLowerCase();
        const industryKeywords = {
            'saas': ['software', 'saas', 'platform', 'api', 'cloud'],
            'ecommerce': ['shop', 'store', 'buy', 'cart', 'checkout', 'ecommerce'],
            'consulting': ['consulting', 'advisory', 'services', 'expertise'],
            'finance': ['finance', 'banking', 'investment', 'financial'],
            'healthcare': ['health', 'medical', 'healthcare', 'clinic', 'hospital'],
            'education': ['education', 'learning', 'school', 'university', 'course'],
            'manufacturing': ['manufacturing', 'industrial', 'production', 'factory'],
            'real estate': ['real estate', 'property', 'housing', 'homes']
        };
        
        for (const [industry, keywords] of Object.entries(industryKeywords)) {
            if (keywords.some(keyword => content.includes(keyword))) {
                companyInfo.industry = industry;
                break;
            }
        }
        
        return companyInfo;
    }
    
    /**
     * Send company info to extension popup when requested
     */
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'getCompanyInfo') {
            const companyInfo = detectCompanyInformation();
            sendResponse(companyInfo);
        }
        return true;
    });
    
    /**
     * Auto-detect when page is loaded (for future features)
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                const companyInfo = detectCompanyInformation();
                console.log('Source-to-Sell detected company:', companyInfo);
            }, 1000);
        });
    } else {
        setTimeout(() => {
            const companyInfo = detectCompanyInformation();
            console.log('Source-to-Sell detected company:', companyInfo);
        }, 1000);
    }
    
    /**
     * Visual indicator (subtle) that extension is active
     */
    function addVisualIndicator() {
        if (document.querySelector('#source-to-sell-indicator')) {
            return; // Already added
        }
        
        const indicator = document.createElement('div');
        indicator.id = 'source-to-sell-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            z-index: 999999;
            opacity: 0.7;
            transition: opacity 0.3s;
            pointer-events: none;
        `;
        
        document.body.appendChild(indicator);
        
        // Fade out after 3 seconds
        setTimeout(() => {
            indicator.style.opacity = '0';
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.parentNode.removeChild(indicator);
                }
            }, 300);
        }, 3000);
    }
    
    // Add indicator when page is ready
    if (document.readyState === 'complete') {
        addVisualIndicator();
    } else {
        window.addEventListener('load', addVisualIndicator);
    }
    
})();