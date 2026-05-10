import * as THREE from "three";

export async function loadSplatScene(
  scene: THREE.Scene,
  splatUrl: string
): Promise<() => Promise<void>> {
  const GaussianSplats3D = await import("@mkkellogg/gaussian-splats-3d");
  const splatViewer = new GaussianSplats3D.DropInViewer({
    gpuAcceleratedSort: false
  });

  scene.add(splatViewer);
  await splatViewer.addSplatScene(splatUrl, {
    format: GaussianSplats3D.SceneFormat.Ply,
    position: [0, 0, 0],
    scale: [1, 1, 1],
    showLoadingUI: false,
    splatAlphaRemovalThreshold: 1
  });

  return async () => {
    scene.remove(splatViewer);
    await splatViewer.dispose();
  };
}
