# Flask Style Template

**Reference only.** This directory is a standalone style/theming reference used during Canopy UI development. It is **not** part of the Canopy runtime — the main app does not import or serve these files. Kept in the repo for theme and CSS reference only.

---

A beautiful, modern Flask template with advanced theming system including dark mode and liquid glass effects.

## Features

### 🎨 **Advanced Theming System**
- **Dark Mode** - Complete dark theme with purple-blue gradient
- **Light Mode** - Clean light theme with subtle shadows
- **Liquid Glass** - Stunning glass morphism effects with backdrop blur
- **Auto Mode** - Automatically switches based on system preference

### 📱 **Mobile-First Responsive Design**
- Perfect mobile experience with iOS Safari optimizations
- Responsive images that scale beautifully on all devices
- Touch-friendly interactions and gestures
- PWA-ready with manifest and app icons

### 🎯 **Modern UI Components**
- Bootstrap 5.3 with custom overrides
- Beautiful gradients and glass effects
- Smooth animations and transitions
- Professional typography and spacing

### 🛠️ **Developer-Friendly**
- Comprehensive debugging tools
- Theme testing functions
- Responsive image testing
- Console logging with visual indicators

## Quick Start

1. **Copy the template files** to your Flask project
2. **Include the base template** in your Jinja2 templates
3. **Add theme switching** to your navigation
4. **Customize colors** in the CSS variables

## File Structure

```
flask-style-template/
├── static/
│   ├── css/
│   │   └── themes.css          # Complete theming system
│   ├── js/
│   │   └── themes.js           # Theme switching and debugging
│   └── icons/
│       └── favicon.svg         # App icon
├── templates/
│   └── base.html               # Base template with all styling
└── README.md                   # This file
```

## Usage

### Base Template
```html
{% extends "base.html" %}
{% block content %}
    <!-- Your content here -->
{% endblock %}
```

### Theme Switching
```html
<select id="theme-selector" class="form-select">
    <option value="dark">Dark Mode</option>
    <option value="light">Light Mode</option>
    <option value="liquid-glass">Liquid Glass</option>
    <option value="auto">Auto</option>
</select>
```

### Debugging Tools
```javascript
// Test all themes
testAllThemes()

// Find light elements in dark mode
debugLightElements()

// Test responsive images
testResponsiveImages()
```

## Customization

### Colors
Edit the CSS variables in `themes.css`:
```css
:root {
    --canopy-primary: #6366f1;           /* Your primary color */
    --canopy-secondary: #8b5cf6;         /* Your secondary color */
    --canopy-accent: #06b6d4;            /* Your accent color */
}
```

### Adding New Themes
1. Add theme variables to `:root`
2. Create `[data-theme="your-theme"]` rules
3. Add theme option to selector
4. Test with `testTheme('your-theme')`

## Browser Support

- ✅ Chrome/Edge (full support)
- ✅ Firefox (full support)
- ✅ Safari (full support with iOS optimizations)
- ✅ Mobile browsers (touch-optimized)

## License

Apache 2.0 License - Feel free to use in any project!