import useSWR from "swr";
import { apiGet } from "@/app/api/config";

export type Ad = {
  id: number;
  title: string;
  city: string;
  is_urgent: boolean;
  budget_min?: string;
  budget_max?: string;
  preferred_date?: string;
};

const normalize = <T>(input: any): T[] => {
  if (!input) return [];
  if (Array.isArray(input)) return input;
  if (input.results) return input.results;
  return [];
};

export function useUrgentAds() {
  const { data, error, isLoading } = useSWR("/ads/?is_urgent=true", apiGet<Ad[]>);
  return {
    ads: normalize<Ad>(data?.data),
    error,
    isLoading,
  };
}
