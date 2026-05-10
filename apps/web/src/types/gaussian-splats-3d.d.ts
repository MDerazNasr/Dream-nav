declare module "@mkkellogg/gaussian-splats-3d" {
  import type * as THREE from "three";

  export const SceneFormat: {
    Ply: number;
    Splat: number;
    KSplat: number;
    Spz: number;
  };

  export class DropInViewer extends THREE.Group {
    constructor(options?: Record<string, unknown>);
    addSplatScene(path: string, options?: Record<string, unknown>): Promise<void>;
    dispose(): Promise<void>;
  }
}
