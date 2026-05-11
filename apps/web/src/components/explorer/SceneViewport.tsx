"use client";

import type { CameraPath, LensMode, ViewerRenderMode } from "@dream-nav/shared";
import { useEffect, useRef, type RefObject } from "react";
import * as THREE from "three";
import { confidenceZoneColors, type ConfidenceZoneArtifacts, zoneCells } from "../../lib/confidence-zones";
import { getLensFov } from "../../lib/lens";
import { loadSplatScene } from "../../lib/splat-loader";
import { createCompletionProjection, type CompletionProjectionTarget } from "./completion-projection";
import type { ViewerCameraPose } from "./viewer-camera";

type SceneViewportProps = {
  cameraPath: CameraPath;
  completionProjection: CompletionProjectionTarget | null;
  lensMode: LensMode;
  overlayEnabled: boolean;
  onCameraPoseChange: (pose: ViewerCameraPose) => void;
  renderMode: ViewerRenderMode;
  restorePose: ViewerCameraPose | null;
  restoreSignal: number;
  resetSignal: number;
  splatUrl: string;
  zoneArtifacts: ConfidenceZoneArtifacts;
};

type ViewportRuntime = {
  camera: THREE.PerspectiveCamera;
  completionProjection: THREE.Mesh | null;
  poseReporter: { emit: (force: boolean) => void };
  rotationState: { pitch: number; yaw: number };
  scene: THREE.Scene;
  startPosition: THREE.Vector3;
};

export function SceneViewport({
  cameraPath,
  completionProjection,
  lensMode,
  overlayEnabled,
  onCameraPoseChange,
  renderMode,
  restorePose,
  restoreSignal,
  resetSignal,
  splatUrl,
  zoneArtifacts
}: SceneViewportProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const completionProjectionRef = useRef(completionProjection);
  const lensModeRef = useRef(lensMode);
  const runtimeRef = useRef<ViewportRuntime | null>(null);

  useEffect(() => {
    completionProjectionRef.current = completionProjection;
    const runtime = runtimeRef.current;
    if (!runtime) {
      return;
    }

    replaceCompletionProjection(runtime, completionProjection, cameraPath, zoneArtifacts);
    return () => {
      removeCompletionProjection(runtime);
    };
  }, [cameraPath, completionProjection, zoneArtifacts]);

  useEffect(() => {
    lensModeRef.current = lensMode;
    const runtime = runtimeRef.current;
    if (!runtime) {
      return;
    }

    runtime.camera.fov = getLensFov(lensMode);
    runtime.camera.updateProjectionMatrix();
    runtime.poseReporter.emit(true);
  }, [lensMode]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) {
      return;
    }

    resetCamera(runtime.camera, runtime.startPosition, runtime.rotationState);
    runtime.poseReporter.emit(true);
  }, [resetSignal]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !restorePose) {
      return;
    }

    applyCameraPose(runtime.camera, restorePose, runtime.rotationState);
    runtime.poseReporter.emit(true);
  }, [restorePose, restoreSignal]);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) {
      return;
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#111412");

    const camera = new THREE.PerspectiveCamera(getLensFov(lensMode), 1, 0.1, 100);
    const startPosition = startCameraPosition(cameraPath);
    const rotationState = { pitch: 0, yaw: 0 };
    resetCamera(camera, startPosition, rotationState);
    const poseReporter = createCameraPoseReporter(camera, rotationState, lensModeRef, onCameraPoseChange);
    runtimeRef.current = {
      camera,
      completionProjection: null,
      poseReporter,
      rotationState,
      scene,
      startPosition
    };
    replaceCompletionProjection(runtimeRef.current, completionProjectionRef.current, cameraPath, zoneArtifacts);
    poseReporter.emit(true);

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.dataset.testid = "scene-canvas";
    renderer.domElement.tabIndex = 0;
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
    const pointerState = { active: false, x: 0, y: 0 };
    const onPointerDown = (event: PointerEvent) => {
      pointerState.active = true;
      pointerState.x = event.clientX;
      pointerState.y = event.clientY;
      renderer.domElement.setPointerCapture(event.pointerId);
      renderer.domElement.focus();
    };
    const onPointerMove = (event: PointerEvent) => {
      if (!pointerState.active) {
        return;
      }

      const dx = event.clientX - pointerState.x;
      const dy = event.clientY - pointerState.y;
      pointerState.x = event.clientX;
      pointerState.y = event.clientY;
      rotateCamera(camera, rotationState, dx, dy);
      poseReporter.emit(false);
    };
    const endPointerLook = (event: PointerEvent) => {
      pointerState.active = false;
      if (renderer.domElement.hasPointerCapture(event.pointerId)) {
        renderer.domElement.releasePointerCapture(event.pointerId);
      }
      poseReporter.emit(true);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup", endPointerLook);
    renderer.domElement.addEventListener("pointercancel", endPointerLook);
    renderer.domElement.addEventListener("lostpointercapture", endPointerLook);

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
      const moved = moveCamera(camera, pressedKeys, delta, rotationState.yaw);
      if (moved) {
        poseReporter.emit(false);
      }
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
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", endPointerLook);
      renderer.domElement.removeEventListener("pointercancel", endPointerLook);
      renderer.domElement.removeEventListener("lostpointercapture", endPointerLook);
      void disposeSplatViewer?.();
      removeCompletionProjection(runtimeRef.current);
      [...objects, ...fallbackObjects].forEach(disposeObjectResources);
      renderer.dispose();
      runtimeRef.current = null;
      mount.replaceChildren();
    };
  }, [cameraPath, onCameraPoseChange, overlayEnabled, renderMode, splatUrl, zoneArtifacts]);

  return (
    <div
      className="viewport"
      data-completion-mask={completionProjection?.maskUrl ? "active" : "inactive"}
      data-completion-projection={completionProjection ? "active" : "inactive"}
      data-completion-projection-pose={completionProjection?.cameraPoseIndex ?? "none"}
      data-testid="scene-viewport"
      ref={mountRef}
    />
  );
}

function replaceCompletionProjection(
  runtime: ViewportRuntime,
  completionProjection: CompletionProjectionTarget | null,
  cameraPath: CameraPath,
  zoneArtifacts: ConfidenceZoneArtifacts
): void {
  removeCompletionProjection(runtime);

  if (!completionProjection) {
    return;
  }

  const projection = createCompletionProjection(completionProjection, cameraPath, zoneArtifacts);
  runtime.scene.add(projection);
  runtime.completionProjection = projection;
}

function removeCompletionProjection(runtime: ViewportRuntime | null): void {
  if (!runtime?.completionProjection) {
    return;
  }

  runtime.scene.remove(runtime.completionProjection);
  disposeObjectResources(runtime.completionProjection);
  runtime.completionProjection = null;
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
    materials.forEach((material) => {
      if ("map" in material && material.map instanceof THREE.Texture) {
        material.map.dispose();
      }
      if ("alphaMap" in material && material.alphaMap instanceof THREE.Texture) {
        material.alphaMap.dispose();
      }
      material.dispose();
    });
  }
}

function moveCamera(
  camera: THREE.PerspectiveCamera,
  pressedKeys: Set<string>,
  delta: number,
  yaw: number
): boolean {
  const speed = (pressedKeys.has("shift") ? 4.2 : 2.4) * delta;
  const forward = new THREE.Vector3(Math.sin(yaw), 0, -Math.cos(yaw));
  const right = new THREE.Vector3(Math.cos(yaw), 0, Math.sin(yaw));
  let moved = false;

  if (pressedKeys.has("w") || pressedKeys.has("arrowup")) {
    camera.position.addScaledVector(forward, speed);
    moved = true;
  }

  if (pressedKeys.has("s") || pressedKeys.has("arrowdown")) {
    camera.position.addScaledVector(forward, -speed);
    moved = true;
  }

  if (pressedKeys.has("a") || pressedKeys.has("arrowleft")) {
    camera.position.addScaledVector(right, -speed);
    moved = true;
  }

  if (pressedKeys.has("d") || pressedKeys.has("arrowright")) {
    camera.position.addScaledVector(right, speed);
    moved = true;
  }

  return moved;
}

function rotateCamera(
  camera: THREE.PerspectiveCamera,
  rotationState: { pitch: number; yaw: number },
  dx: number,
  dy: number
): void {
  rotationState.yaw -= dx * 0.003;
  rotationState.pitch = Math.max(-1.2, Math.min(1.2, rotationState.pitch - dy * 0.003));
  camera.rotation.order = "YXZ";
  camera.rotation.y = rotationState.yaw;
  camera.rotation.x = rotationState.pitch;
}

function createCameraPoseReporter(
  camera: THREE.PerspectiveCamera,
  rotationState: { pitch: number; yaw: number },
  lensModeRef: RefObject<LensMode>,
  onCameraPoseChange: (pose: ViewerCameraPose) => void
): { emit: (force: boolean) => void } {
  let lastEmitTime = 0;

  return {
    emit: (force) => {
      const now = performance.now();
      if (!force && now - lastEmitTime < 120) {
        return;
      }

      lastEmitTime = now;
      const lensMode = lensModeRef.current;
      onCameraPoseChange({
        fovDegrees: getLensFov(lensMode),
        lensMode,
        pitch: rotationState.pitch,
        position: [camera.position.x, camera.position.y, camera.position.z],
        yaw: rotationState.yaw
      });
    }
  };
}

function resetCamera(
  camera: THREE.PerspectiveCamera,
  startPosition: THREE.Vector3,
  rotationState: { pitch: number; yaw: number }
): void {
  rotationState.pitch = 0;
  rotationState.yaw = 0;
  camera.position.copy(startPosition);
  camera.rotation.order = "YXZ";
  camera.rotation.set(0, 0, 0);
}

function applyCameraPose(
  camera: THREE.PerspectiveCamera,
  pose: ViewerCameraPose,
  rotationState: { pitch: number; yaw: number }
): void {
  rotationState.pitch = pose.pitch;
  rotationState.yaw = pose.yaw;
  camera.position.set(pose.position[0], pose.position[1], pose.position[2]);
  camera.rotation.order = "YXZ";
  camera.rotation.y = pose.yaw;
  camera.rotation.x = pose.pitch;
}

function startCameraPosition(cameraPath: CameraPath): THREE.Vector3 {
  const startPose = cameraPath.poses[0];
  return new THREE.Vector3(
    startPose?.position[0] ?? 0,
    startPose?.position[1] ?? 1.55,
    startPose?.position[2] ?? 3
  );
}
