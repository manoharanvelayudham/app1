import React, { useState, useEffect } from 'react';
import { Palette, Save, RotateCcw, Eye, Download } from 'lucide-react';
import { defaultTheme, themePresets, createCustomTheme, applyThemeToDocument } from '../../theme';
import LogoUpload from './LogoUpload';

const ThemeCustomizer = ({ onThemeChange, currentTheme = defaultTheme }) => {
  const [theme, setTheme] = useState(currentTheme);
  const [activePreset, setActivePreset] = useState('default');
  const [showPreview, setShowPreview] = useState(false);
  const [customColors, setCustomColors] = useState({
    primary: currentTheme.colors.primary[500],
    secondary: currentTheme.colors.secondary[500],
    success: currentTheme.colors.success[500],
    warning: currentTheme.colors.warning[500],
    error: currentTheme.colors.error[500],
  });

  const handleColorChange = (colorType, value) => {
    setCustomColors(prev => ({
      ...prev,
      [colorType]: value
    }));

    // Generate color shades based on the main color
    const newTheme = createCustomTheme({
      colors: {
        [colorType]: generateColorShades(value)
      }
    });

    setTheme(newTheme);
    if (onThemeChange) {
      onThemeChange(newTheme);
    }
  };

  const handleBrandingChange = (field, value) => {
    const newTheme = {
      ...theme,
      branding: {
        ...theme.branding,
        [field]: value
      }
    };
    
    setTheme(newTheme);
    if (onThemeChange) {
      onThemeChange(newTheme);
    }
  };

  const handlePresetChange = (presetName) => {
    setActivePreset(presetName);
    
    if (presetName === 'default') {
      setTheme(defaultTheme);
      setCustomColors({
        primary: defaultTheme.colors.primary[500],
        secondary: defaultTheme.colors.secondary[500],
        success: defaultTheme.colors.success[500],
        warning: defaultTheme.colors.warning[500],
        error: defaultTheme.colors.error[500],
      });
    } else {
      const preset = themePresets[presetName];
      const newTheme = createCustomTheme(preset);
      setTheme(newTheme);
      
      // Update custom colors to match preset
      setCustomColors({
        primary: preset.colors?.primary?.[500] || defaultTheme.colors.primary[500],
        secondary: defaultTheme.colors.secondary[500],
        success: defaultTheme.colors.success[500],
        warning: defaultTheme.colors.warning[500],
        error: defaultTheme.colors.error[500],
      });
    }
    
    if (onThemeChange) {
      onThemeChange(theme);
    }
  };

  const generateColorShades = (baseColor) => {
    // Simple color shade generation (in production, use a proper color library)
    const shades = {};
    const variations = [
      { key: '50', lightness: 0.95 },
      { key: '100', lightness: 0.9 },
      { key: '200', lightness: 0.8 },
      { key: '300', lightness: 0.7 },
      { key: '400', lightness: 0.6 },
      { key: '500', lightness: 0.5 },
      { key: '600', lightness: 0.4 },
      { key: '700', lightness: 0.3 },
      { key: '800', lightness: 0.2 },
      { key: '900', lightness: 0.1 },
    ];

    variations.forEach(({ key, lightness }) => {
      if (key === '500') {
        shades[key] = baseColor;
      } else {
        // Simple lightness adjustment (this is a basic implementation)
        shades[key] = adjustColorLightness(baseColor, lightness);
      }
    });

    return shades;
  };

  const adjustColorLightness = (color, lightness) => {
    // Convert hex to HSL, adjust lightness, convert back
    // This is a simplified version - use a proper color library in production
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16) / 255;
    const g = parseInt(hex.substr(2, 2), 16) / 255;
    const b = parseInt(hex.substr(4, 2), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = lightness;
    const s = max === min ? 0 : l > 0.5 ? (max - min) / (2 - max - min) : (max - min) / (max + min);

    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };

    let h;
    if (max === min) {
      h = 0;
    } else {
      switch (max) {
        case r: h = (g - b) / (max - min) + (g < b ? 6 : 0); break;
        case g: h = (b - r) / (max - min) + 2; break;
        case b: h = (r - g) / (max - min) + 4; break;
      }
      h /= 6;
    }

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    
    const newR = Math.round(hue2rgb(p, q, h + 1/3) * 255);
    const newG = Math.round(hue2rgb(p, q, h) * 255);
    const newB = Math.round(hue2rgb(p, q, h - 1/3) * 255);

    return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
  };

  const handleLogoUpload = (logoData) => {
    handleBrandingChange('logo', logoData?.file);
    handleBrandingChange('logoUrl', logoData?.url);
  };

  const resetToDefault = () => {
    setTheme(defaultTheme);
    setActivePreset('default');
    setCustomColors({
      primary: defaultTheme.colors.primary[500],
      secondary: defaultTheme.colors.secondary[500],
      success: defaultTheme.colors.success[500],
      warning: defaultTheme.colors.warning[500],
      error: defaultTheme.colors.error[500],
    });
    if (onThemeChange) {
      onThemeChange(defaultTheme);
    }
  };

  const exportTheme = () => {
    const themeConfig = JSON.stringify(theme, null, 2);
    const blob = new Blob([themeConfig], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'theme-config.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const previewTheme = () => {
    if (showPreview) {
      // Restore original theme
      applyThemeToDocument(currentTheme);
    } else {
      // Apply current theme
      applyThemeToDocument(theme);
    }
    setShowPreview(!showPreview);
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Theme Customization</h2>
        <div className="flex space-x-2">
          <button
            onClick={previewTheme}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <Eye className="w-4 h-4 mr-2" />
            {showPreview ? 'Stop Preview' : 'Preview'}
          </button>
          <button
            onClick={exportTheme}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          <button
            onClick={resetToDefault}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </button>
        </div>
      </div>

      {/* Theme Presets */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Industry Presets</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <button
            onClick={() => handlePresetChange('default')}
            className={`p-3 rounded-lg border-2 text-center transition-colors ${
              activePreset === 'default'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="w-6 h-6 bg-blue-500 rounded mx-auto mb-2"></div>
            <span className="text-sm font-medium">Default</span>
          </button>
          
          {Object.entries(themePresets).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => handlePresetChange(key)}
              className={`p-3 rounded-lg border-2 text-center transition-colors ${
                activePreset === key
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div 
                className="w-6 h-6 rounded mx-auto mb-2"
                style={{ backgroundColor: preset.colors.primary[500] }}
              ></div>
              <span className="text-sm font-medium capitalize">{key}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Branding */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Branding</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <LogoUpload
              onLogoUpload={handleLogoUpload}
              currentLogo={theme.branding.logoUrl}
            />
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Company Name
              </label>
              <input
                type="text"
                value={theme.branding.companyName}
                onChange={(e) => handleBrandingChange('companyName', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter company name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tagline
              </label>
              <input
                type="text"
                value={theme.branding.tagline}
                onChange={(e) => handleBrandingChange('tagline', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter tagline"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Color Customization */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Color Scheme</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {Object.entries(customColors).map(([colorType, color]) => (
            <div key={colorType} className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 capitalize">
                {colorType}
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => handleColorChange(colorType, e.target.value)}
                  className="w-12 h-10 border border-gray-300 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={color}
                  onChange={(e) => handleColorChange(colorType, e.target.value)}
                  className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Preview */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Preview</h3>
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="flex items-center space-x-3 mb-4">
            {theme.branding.logoUrl && (
              <img
                src={theme.branding.logoUrl}
                alt="Logo"
                className="h-8 object-contain"
              />
            )}
            <div>
              <h4 className="font-semibold text-gray-900">{theme.branding.companyName}</h4>
              <p className="text-sm text-gray-600">{theme.branding.tagline}</p>
            </div>
          </div>
          
          <div className="flex space-x-2 mb-4">
            <button
              className="px-4 py-2 text-white rounded-md"
              style={{ backgroundColor: customColors.primary }}
            >
              Primary Button
            </button>
            <button
              className="px-4 py-2 text-white rounded-md"
              style={{ backgroundColor: customColors.secondary }}
            >
              Secondary Button
            </button>
          </div>
          
          <div className="flex space-x-2">
            <div
              className="px-3 py-1 text-white text-sm rounded-full"
              style={{ backgroundColor: customColors.success }}
            >
              Success
            </div>
            <div
              className="px-3 py-1 text-white text-sm rounded-full"
              style={{ backgroundColor: customColors.warning }}
            >
              Warning
            </div>
            <div
              className="px-3 py-1 text-white text-sm rounded-full"
              style={{ backgroundColor: customColors.error }}
            >
              Error
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThemeCustomizer;
