import React from 'react';
import atlasLogoImg from '../assets/atlas-logo.png';

export default function AtlasLogo({ className = "w-6 h-6", alt = "Atlas", style = {} }) {
  return (
    <img
      src={atlasLogoImg}
      alt={alt}
      className={`object-contain shrink-0 select-none ${className}`}
      style={style}
    />
  );
}
