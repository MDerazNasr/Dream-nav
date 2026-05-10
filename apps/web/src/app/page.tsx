import { loadSceneBundle } from "@dream-nav/scene-registry";
import { ExplorerShell } from "../components/explorer/ExplorerShell";

export default async function HomePage() {
  const sceneBundle = await loadSceneBundle("warehouse_01");

  return <ExplorerShell sceneBundle={sceneBundle} />;
}
