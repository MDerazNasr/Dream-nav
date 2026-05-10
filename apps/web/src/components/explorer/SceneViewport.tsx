"use client";

import type { CameraPath, LensMode, VisibilityManifest } from "@dream-nav/shared";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { getLensFov } from "../../lib/lens";

type SceneViewportProps = {
  cameraPath: CameraPath;
  lensMode: LensMode;
  overlayEnabled: boolean;
  visibility: VisibilityManifest;
};

export function SceneViewport({
  cameraPath,
  lensMode,
  overlayEnabled,
  visibility
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

    const objects = createPlaceholderScene(visibility, overlayEnabled);
    objects.forEach((object) => scene.add(object));

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

    const clock = new THREE.Clock();
    let animationFrame = 0;

    const render = () => {
      const delta = clock.getDelta();
      moveCamera(camera, pressedKeys, delta);
      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(render);
    };

    resize();
    render();
    window.addEventListener("resize", resize);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      renderer.dispose();
      mount.replaceChildren();
    };
  }, [cameraPath, lensMode, overlayEnabled, visibility]);

  return <div className="viewport" data-testid="scene-viewport" ref={mountRef} />;
}

function createPlaceholderScene(visibility: VisibilityManifest, overlayEnabled: boolean): THREE.Object3D[] {
  const objects: THREE.Object3D[] = [];
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 16),
    new THREE.MeshStandardMaterial({ color: "#2a2f2b", roughness: 0.82 })
  );
  floor.rotation.x = -Math.PI / 2;
  objects.push(floor);

  visibility.cells.forEach((cell) => {
    const material = new THREE.MeshStandardMaterial({
      color: overlayEnabled ? zoneColor(cell.zone) : "#8d948c",
      opacity: overlayEnabled && cell.zone !== "observed" ? 0.72 : 1,
      transparent: overlayEnabled && cell.zone !== "observed"
    });
    const cube = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.45, 0.45), material);
    cube.position.set(cell.center[0], cell.center[1], cell.center[2]);
    objects.push(cube);
  });

  return objects;
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

function zoneColor(zone: string): string {
  if (zone === "observed") {
    return "#dfe7df";
  }

  if (zone === "partial") {
    return "#77d7c8";
  }

  if (zone === "completion") {
    return "#4a8ee8";
  }

  return "#d88b4a";
}
