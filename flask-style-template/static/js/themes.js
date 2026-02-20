// Flask Style Template - Theme Management & Debugging

// Dynamic viewport height calculation for mobile
function setVH() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Set initial VH and update on resize
setVH();
window.addEventListener('resize', setVH);

// Theme Management
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('flask-theme', theme);
    
    // Enhanced logging
    console.log('🎨 Applied theme:', theme);
    console.log('🔍 Document data-theme attribute:', document.documentElement.getAttribute('data-theme'));
    
    // Force a style recalculation
    document.documentElement.offsetHeight;
    
    // Log some test elements to see if styling is applied
    setTimeout(() => {
        const testCard = document.querySelector('.card');
        const testBtn = document.querySelector('.btn');
        if (testCard) {
            const cardStyles = window.getComputedStyle(testCard);
            console.log('🃏 Card background:', cardStyles.backgroundColor);
            console.log('🃏 Card color:', cardStyles.color);
        }
        if (testBtn) {
            const btnStyles = window.getComputedStyle(testBtn);
            console.log('🔲 Button background:', btnStyles.backgroundColor);
            console.log('🔲 Button color:', btnStyles.color);
        }
    }, 100);
}

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('flask-theme') || 'dark';
    
    // Handle auto theme - detect system preference
    if (savedTheme === 'auto') {
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(systemPrefersDark ? 'dark' : 'light');
        
        // Watch for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (localStorage.getItem('flask-theme') === 'auto') {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    } else {
        applyTheme(savedTheme);
    }
}

// Load theme on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSavedTheme();
});

// Apply theme immediately (before DOM content loaded)
(function() {
    const savedTheme = localStorage.getItem('flask-theme') || 'dark';
    console.log('🚀 Early theme application:', savedTheme);
    if (savedTheme !== 'auto') {
        document.documentElement.setAttribute('data-theme', savedTheme);
        console.log('✅ Set data-theme attribute to:', savedTheme);
    }
})();

// Theme selector functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeSelector = document.getElementById('theme-selector');
    if (themeSelector) {
        // Set current theme in selector
        const currentTheme = localStorage.getItem('flask-theme') || 'dark';
        themeSelector.value = currentTheme;
        
        // Handle theme changes
        themeSelector.addEventListener('change', function() {
            const selectedTheme = this.value;
            applyTheme(selectedTheme);
        });
    }
});

// Sidebar Management
document.addEventListener('DOMContentLoaded', function() {
    const sidebarContainer = document.getElementById('sidebar-container');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    
    if (sidebarContainer && sidebarToggle) {
        // Load saved sidebar state
        const savedState = localStorage.getItem('sidebar-state') || 'expanded';
        sidebarContainer.className = `sidebar-container ${savedState}`;
        
        // Toggle sidebar
        sidebarToggle.addEventListener('click', function() {
            const currentState = sidebarContainer.className.includes('expanded') ? 'expanded' :
                               sidebarContainer.className.includes('collapsed') ? 'collapsed' : 'hidden';
            
            let newState;
            if (currentState === 'expanded') {
                newState = 'collapsed';
            } else if (currentState === 'collapsed') {
                newState = 'hidden';
            } else {
                newState = 'expanded';
            }
            
            sidebarContainer.className = `sidebar-container ${newState}`;
            localStorage.setItem('sidebar-state', newState);
        });
        
        // Keyboard shortcut (Ctrl+B / Cmd+B)
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                sidebarToggle.click();
            }
        });
    }
});

// Mobile swipe gestures for sidebar
document.addEventListener('DOMContentLoaded', function() {
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        const sidebarContainer = document.getElementById('sidebar-container');
        if (!sidebarContainer) return;
        
        const swipeThreshold = 50;
        const swipeDistance = touchEndX - touchStartX;
        
        // Only handle swipes on mobile
        if (window.innerWidth <= 768) {
            if (swipeDistance > swipeThreshold && touchStartX < 50) {
                // Swipe right from left edge - open sidebar
                sidebarContainer.className = 'sidebar-container expanded';
                localStorage.setItem('sidebar-state', 'expanded');
            } else if (swipeDistance < -swipeThreshold && touchStartX < 100) {
                // Swipe left from left area - close sidebar
                sidebarContainer.className = 'sidebar-container collapsed';
                localStorage.setItem('sidebar-state', 'collapsed');
            }
        }
    }
});

// Debug function to find elements with light backgrounds
function debugLightElements() {
    const lightElements = [];
    const allElements = document.querySelectorAll('*');
    
    allElements.forEach(el => {
        const styles = window.getComputedStyle(el);
        const bgColor = styles.backgroundColor;
        const color = styles.color;
        
        // Check for light backgrounds (white, light gray, etc.)
        if (bgColor && (
            bgColor.includes('rgb(255, 255, 255)') || 
            bgColor.includes('rgba(255, 255, 255') ||
            bgColor.includes('#fff') ||
            bgColor.includes('#ffffff') ||
            bgColor.includes('white') ||
            (bgColor.includes('rgb(') && 
             bgColor.split(',').every(part => {
                const num = parseInt(part.replace(/[^\d]/g, ''));
                return num > 200; // Light colors
             }))
        )) {
            lightElements.push({
                element: el,
                tagName: el.tagName,
                className: el.className,
                backgroundColor: bgColor,
                color: color,
                id: el.id || 'no-id'
            });
        }
    });
    
    console.log('🔍 Found', lightElements.length, 'elements with light backgrounds:');
    lightElements.forEach((item, index) => {
        console.log(`${index + 1}. ${item.tagName}.${item.className} (${item.id})`, 
            `bg: ${item.backgroundColor}`, item.element);
    });
    
    return lightElements;
}

// Add debug function to window for manual testing
window.debugLightElements = debugLightElements;

// Quick theme switching for testing
window.testTheme = function(theme) {
    console.log('🧪 Testing theme:', theme);
    applyTheme(theme);
    setTimeout(() => {
        console.log('🔍 Checking for light elements after theme change...');
        debugLightElements();
    }, 500);
};

// Quick test all themes
window.testAllThemes = function() {
    const themes = ['dark', 'light', 'liquid-glass', 'auto'];
    let index = 0;
    
    function nextTheme() {
        if (index < themes.length) {
            console.log(`🎨 Testing theme ${index + 1}/${themes.length}: ${themes[index]}`);
            testTheme(themes[index]);
            index++;
            setTimeout(nextTheme, 3000); // Wait 3 seconds between themes
        } else {
            console.log('✅ All themes tested!');
        }
    }
    
    nextTheme();
};

// Test responsive image sizing
window.testResponsiveImages = function() {
    const images = document.querySelectorAll('.message-image, .post-image, .channel-image, .comment-image img');
    console.log(`📱 Found ${images.length} responsive images`);
    
    images.forEach((img, index) => {
        const computedStyle = window.getComputedStyle(img);
        const maxWidth = computedStyle.maxWidth;
        const maxHeight = computedStyle.maxHeight;
        const actualWidth = img.offsetWidth;
        const actualHeight = img.offsetHeight;
        
        console.log(`${index + 1}. ${img.className}:`, {
            maxWidth,
            maxHeight,
            actualSize: `${actualWidth}x${actualHeight}px`,
            element: img
        });
    });
    
    // Test different screen sizes simulation
    const viewportWidth = window.innerWidth;
    console.log(`📏 Current viewport: ${viewportWidth}px`);
    if (viewportWidth <= 375) {
        console.log('📱 Small phone mode active');
    } else if (viewportWidth <= 576) {
        console.log('📱 Mobile phone mode active');
    } else if (viewportWidth <= 768) {
        console.log('📱 Tablet mode active');
    } else {
        console.log('🖥️ Desktop mode active');
    }
};

// Auto-run debug after theme is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        console.log('🔍 Running automatic light element detection...');
        debugLightElements();
    }, 1000);
});

// Prevent elastic scrolling on iOS
document.addEventListener('touchmove', function(e) {
    if (e.target.closest('.main-content')) {
        // Allow scrolling in main content
        return;
    }
    // Prevent elastic scrolling elsewhere
    e.preventDefault();
}, { passive: false });

// Handle iOS safe areas
function setSafeAreas() {
    const safeTop = getComputedStyle(document.documentElement).getPropertyValue('--sat') || '0px';
    const safeBottom = getComputedStyle(document.documentElement).getPropertyValue('--sab') || '0px';
    const safeLeft = getComputedStyle(document.documentElement).getPropertyValue('--sal') || '0px';
    const safeRight = getComputedStyle(document.documentElement).getPropertyValue('--sar') || '0px';
    
    document.documentElement.style.setProperty('--safe-top', safeTop);
    document.documentElement.style.setProperty('--safe-bottom', safeBottom);
    document.documentElement.style.setProperty('--safe-left', safeLeft);
    document.documentElement.style.setProperty('--safe-right', safeRight);
}

// Set safe areas on load and resize
setSafeAreas();
window.addEventListener('resize', setSafeAreas);

// PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(registration) {
                console.log('✅ ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('❌ ServiceWorker registration failed');
            });
    });
}

// Export functions for use in other scripts
window.FlaskTheme = {
    applyTheme,
    loadSavedTheme,
    debugLightElements,
    testTheme,
    testAllThemes,
    testResponsiveImages
}; 