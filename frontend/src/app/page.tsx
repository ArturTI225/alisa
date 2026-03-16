import { apiGet } from "./api/config";
import { LandingClient } from "@/components/LandingClient";
import { Service } from "@/hooks/useServices";
import { Ad } from "@/hooks/useAds";
import { Provider } from "@/hooks/useProviders";

export const revalidate = 30;

export default async function Page() {
  const [servicesRes, adsRes, providersRes] = await Promise.all([
    apiGet<Service[]>("/services/"),
    apiGet<Ad[]>("/ads/?is_urgent=true"),
    apiGet<Provider[]>("/providers/?ordering=-rating_avg&min_rating=4"),
  ]);

  return (
    <LandingClient
      initialServices={servicesRes.data || []}
      initialAds={adsRes.data || []}
      initialProviders={providersRes.data || []}
    />
  );
}
