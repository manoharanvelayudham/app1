// Enterprise Theme Configuration
export const defaultTheme = {
  colors: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    secondary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d',
    },
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
    },
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444',
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d',
    },
  },
  branding: {
    companyName: 'Corporate Wellness Platform',
    tagline: 'Empowering Growth Through AI',
    logo: null, // Will be set via logo upload
    logoUrl: null,
    favicon: null,
  },
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'monospace'],
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem',
    },
  },
  layout: {
    sidebar: {
      width: '256px',
      collapsedWidth: '64px',
    },
    header: {
      height: '64px',
    },
    borderRadius: {
      sm: '0.375rem',
      md: '0.5rem',
      lg: '0.75rem',
      xl: '1rem',
    },
  },
  animations: {
    transition: {
      fast: '150ms ease-in-out',
      normal: '300ms ease-in-out',
      slow: '500ms ease-in-out',
    },
  },
};

// White-label theme customization
export const createCustomTheme = (customizations = {}) => {
  return {
    ...defaultTheme,
    colors: {
      ...defaultTheme.colors,
      ...customizations.colors,
    },
    branding: {
      ...defaultTheme.branding,
      ...customizations.branding,
    },
    typography: {
      ...defaultTheme.typography,
      ...customizations.typography,
    },
    layout: {
      ...defaultTheme.layout,
      ...customizations.layout,
    },
  };
};

// Theme presets for different industries
export const themePresets = {
  healthcare: {
    colors: {
      primary: {
        500: '#059669', // Green
        600: '#047857',
        700: '#065f46',
      },
    },
    branding: {
      companyName: 'Healthcare Wellness Hub',
      tagline: 'Caring for Your Team\'s Wellbeing',
    },
  },
  finance: {
    colors: {
      primary: {
        500: '#1f2937', // Dark Gray
        600: '#111827',
        700: '#030712',
      },
    },
    branding: {
      companyName: 'Financial Wellness Solutions',
      tagline: 'Building Stronger Financial Futures',
    },
  },
  technology: {
    colors: {
      primary: {
        500: '#7c3aed', // Purple
        600: '#6d28d9',
        700: '#5b21b6',
      },
    },
    branding: {
      companyName: 'Tech Wellness Platform',
      tagline: 'Innovation Meets Wellbeing',
    },
  },
  education: {
    colors: {
      primary: {
        500: '#ea580c', // Orange
        600: '#dc2626',
        700: '#b91c1c',
      },
    },
    branding: {
      companyName: 'Educational Wellness Center',
      tagline: 'Nurturing Growth and Learning',
    },
  },
};

// CSS-in-JS utility for generating theme variables
export const generateThemeCSS = (theme) => {
  const cssVars = {};
  
  // Generate color variables
  Object.entries(theme.colors).forEach(([colorName, colorShades]) => {
    if (typeof colorShades === 'object') {
      Object.entries(colorShades).forEach(([shade, value]) => {
        cssVars[`--color-${colorName}-${shade}`] = value;
      });
    }
  });
  
  // Generate typography variables
  Object.entries(theme.typography.fontSize).forEach(([size, value]) => {
    cssVars[`--font-size-${size}`] = value;
  });
  
  // Generate layout variables
  cssVars['--sidebar-width'] = theme.layout.sidebar.width;
  cssVars['--sidebar-collapsed-width'] = theme.layout.sidebar.collapsedWidth;
  cssVars['--header-height'] = theme.layout.header.height;
  
  return cssVars;
};

// Theme context utilities
export const getThemeValue = (theme, path) => {
  return path.split('.').reduce((obj, key) => obj?.[key], theme);
};

export const applyThemeToDocument = (theme) => {
  const cssVars = generateThemeCSS(theme);
  const root = document.documentElement;
  
  Object.entries(cssVars).forEach(([property, value]) => {
    root.style.setProperty(property, value);
  });
  
  // Update document title and favicon if provided
  if (theme.branding.companyName) {
    document.title = theme.branding.companyName;
  }
  
  if (theme.branding.favicon) {
    const favicon = document.querySelector('link[rel="icon"]') || document.createElement('link');
    favicon.rel = 'icon';
    favicon.href = theme.branding.favicon;
    document.head.appendChild(favicon);
  }
};

export default defaultTheme;
