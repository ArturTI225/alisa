import useSWR from "swr";
import { apiGet } from "@/app/api/config";

export type Provider = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  rating_avg: string | number;
  rating_count: number;
  city?: string;
  provider_profile?: {
    skills?: { name: string }[];
  };
};

const normalize = <T>(input: any): T[] => {
  if (!input) return [];
  if (Array.isArray(input)) return input;
  if (input.results) return input.results;
  return [];
};

export function useProviders(minRating = 4) {
  const { data, error, isLoading } = useSWR(
    `/providers/?ordering=-rating_avg&min_rating=${minRating}`,
    apiGet<Provider[]>
  );
  return {
    providers: normalize<Provider>(data?.data),
    error,
    isLoading,
  };
}
