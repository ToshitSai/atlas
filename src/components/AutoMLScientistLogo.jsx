import React from 'react';
import AtlasLogo from './AtlasLogo';

export default function AutoMLScientistLogo({ size = "md" }) {
  const logoDimensions = size === "lg" ? "w-10 h-10" : size === "sm" ? "w-5 h-5" : "w-7 h-7";
  
  return (
    <div className="flex items-center gap-3 select-none">
      <AtlasLogo className={`${logoDimensions} shrink-0`} />
      <div>
        <div className="font-semibold text-slate-100 tracking-tight text-sm leading-none flex items-center gap-1.5">
          Atlas
        </div>
        <div className="text-[10px] font-mono tracking-wider text-[#F15A3A]/90 font-medium uppercase mt-0.5">
          Autonomous ML Research
        </div>
      </div>
    </div>
  );
}
