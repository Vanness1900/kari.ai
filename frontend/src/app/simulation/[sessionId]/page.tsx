import { LiveSimulationView } from "@/components/simulation/live-simulation-view";

export default async function SimulationPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <LiveSimulationView sessionId={sessionId} />;
}
