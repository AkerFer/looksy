import { OutfitResults } from "@/components/outfits";
export default async function Page({
  params,
}: {
  params: Promise<{ ids: string }>;
}) {
  const { ids } = await params;
  return <OutfitResults ids={ids} />;
}
