"use client";

import type { CameraPath, LensMode, ViewerRenderMode } from "@dream-nav/shared";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { confidenceZoneColors, type ConfidenceZoneArtifacts, zoneCells } from "../../lib/confidence-zones";
import { getLensFov } from "../../lib/lens";
import { loadSplatScene } from "../../lib/splat-loader";

type SceneViewportProps = {
  cameraPath: CameraPath;
  lensMode: LensMode;
  overlayEnabled: boolean;
  renderMode: ViewerRenderMode;
  splatUrl: string;
  zoneArtifacts: ConfidenceZoneArtifacts;
};

export function SceneViewport({
  cameraPath,
  lensMode,
  overlayEnabled,
  renderMode,
  splatUrl,
  zoneArtifacts
}: SceneViewportProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) {
      return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#111412");

    const camera = new THREE.PerspectiveCamera(getLensFov(lensMode), 1, 0.1, 100);
    const startPose = cameraPath.poses[0];
    camera.position.set(
      startPose?.position[0] ?? 0,
      startPose?.position[1] ?? 1.55,
      startPose?.position[2] ?? 3
    );

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.dataset.testid = "scene-canvas";
    mount.appendChild(renderer.domElement);

    const objects = createSceneObjects(zoneArtifacts, overlayEnabled, renderMode);
    objects.forEach((object) => scene.add(object));
    const fallbackObjects: THREE.Object3D[] = [];
    let disposeSplatViewer: (() => Promise<void>) | null = null;
    let cleanupStarted = false;

    if (renderMode === "splat") {
      void loadSplatScene(scene, splatUrl)
        .then((dispose) => {
          if (cleanupStarted) {
            void dispose();
            return;
          }

          disposeSplatViewer = dispose;
        })
        .catch(() => {
          if (cleanupStarted) {
            return;
          }

          if (!overlayEnabled) {
            fallbackObjects.push(...createVisibilityObjects(zoneArtifacts, true));
          }
          fallbackObjects.forEach((object) => scene.add(object));
        });
    }

    const light = new THREE.HemisphereLight("#f5f7f4", "#24312d", 1.8);
    scene.add(light);

    const pressedKeys = new Set<string>();
    const onKeyDown = (event: KeyboardEvent) => pressedKeys.add(event.key.toLowerCase());
    const onKeyUp = (event: KeyboardEvent) => pressedKeys.delete(event.key.toLowerCase());
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const resize = () => {
      const bounds = mount.getBoundingClientRect();
      const width = Math.max(1, bounds.width);
      const height = Math.max(1, bounds.height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    let animationFrame = 0;
    let previousFrameTime = performance.now();

    const render = () => {
      const currentFrameTime = performance.now();
      const delta = (currentFrameTime - previousFrameTime) / 1000;
      previousFrameTime = currentFrameTime;
      moveCamera(camera, pressedKeys, delta);
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(render);
    };

    resize();
    render();
    window.addEventListener("resize", resize);

    return () => {
      cleanupStarted = true;
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      void disposeSplatViewer?.();
      [...objects, ...fallbackObjects].forEach(disposeObjectResources);
      renderer.dispose();
      mount.replaceChildren();
    };
  }, [cameraPath, lensMode, overlayEnabled, renderMode, splatUrl, zoneArtifacts]);

  return <div className="viewport" data-testid="scene-viewport" ref={mountRef} />;
}

function createSceneObjects(
  zoneArtifacts: ConfidenceZoneArtifacts,
  overlayEnabled: boolean,
  renderMode: ViewerRenderMode
): THREE.Object3D[] {
  const objects: THREE.Object3D[] = [];
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 16),
    new THREE.MeshStandardMaterial({
      color: renderMode === "splat" ? "#242c28" : "#2a2f2b",
      roughness: 0.82
    })
  );
  floor.rotation.x = -Math.PI / 2;
  objects.push(floor);

  if (renderMode === "placeholder" || overlayEnabled) {
    objects.push(...createVisibilityObjects(zoneArtifacts, overlayEnabled));
  }

  return objects;
}

function createVisibilityObjects(
  zoneArtifacts: ConfidenceZoneArtifacts,
  overlayEnabled: boolean
): THREE.Object3D[] {
  // Limit overlay meshes because the splat renderer already owns the dense scene.
  return zoneCells(zoneArtifacts).slice(0, 128).map((cell) => {
    const material = new THREE.MeshStandardMaterial({
      color: overlayEnabled ? confidenceZoneColors[cell.zone] : "#8d948c",
      opacity: overlayEnabled && cell.zone !== "observed" ? 0.72 : 1,
      transparent: overlayEnabled && cell.zone !== "observed"
    });
    const cube = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.45, 0.45), material);
    cube.position.set(cell.center[0], cell.center[1], cell.center[2]);
    return cube;
  });
}

function disposeObjectResources(object: THREE.Object3D): void {
  if (object instanceof THREE.Mesh) {
    object.geometry.dispose();
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    materials.forEach((material) => material.dispose());
  }
}

function moveCamera(
  camera: THREE.PerspectiveCamera,
  pressedKeys: Set<string>,
  delta: number
): void {
  const speed = 2.4 * delta;

  if (pressedKeys.has("w")) {
    camera.position.z -= speed;
  }

  if (pressedKeys.has("s")) {
    camera.position.z += speed;
  }

  if (pressedKeys.has("a")) {
    camera.position.x -= speed;
  }

  if (pressedKeys.has("d")) {
    camera.position.x += speed;
  }
}
