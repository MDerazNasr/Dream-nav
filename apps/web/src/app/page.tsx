import { WorkflowShell } from "../components/workflow/WorkflowShell";
import { fetchSceneBundle } from "../lib/dreamnav-api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const sceneBundle = await fetchSceneBundle("warehouse_01");

  return <WorkflowShell sceneBundle={sceneBundle} />;
}
