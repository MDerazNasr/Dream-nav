import { WorkflowShell } from "../components/workflow/WorkflowShell";
import { fetchFeaturedSceneBundle, fetchReconstructionCapabilities, fetchSceneBundle } from "../lib/dreamnav-api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [sceneBundle, reconstructionCapabilities] = await Promise.all([
    fetchFeaturedSceneBundle().catch(() => fetchSceneBundle("warehouse_01")),
    fetchReconstructionCapabilities()
  ]);

  return <WorkflowShell reconstructionCapabilities={reconstructionCapabilities} sceneBundle={sceneBundle} />;
}
