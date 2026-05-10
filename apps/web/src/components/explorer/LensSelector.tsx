"use client";

import type { LensMode } from "@dream-nav/shared";

type LensSelectorProps = {
  availableModes: LensMode[];
  selectedLens: LensMode;
  onSelect: (lensMode: LensMode) => void;
};

export function LensSelector({ availableModes, selectedLens, onSelect }: LensSelectorProps) {
  return (
    <div className="lens-selector">
      {availableModes.map((lensMode) => (
        <button
          aria-pressed={selectedLens === lensMode}
          className="lens-button"
          data-active={selectedLens === lensMode}
          key={lensMode}
          onClick={() => onSelect(lensMode)}
          type="button"
        >
          {lensMode}
        </button>
      ))}
    </div>
  );
}
