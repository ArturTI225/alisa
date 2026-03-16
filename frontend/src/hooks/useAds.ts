import useSWR from "swr";
import { apiGet } from "@/app/api/config";

export type Ad = {
  id: number;
  title: string;
  city: string;
  is_urgent: boolean;
  preferred_date?: string;
};

const normalize = <T>(input: any): T[] => {
  if (!input) return [];
  if (Array.isArray(input)) return input;
  if (input.results) return input.results;
  return [];
};

export function useUrgentAds(initialData?: any) {
  const { data, error, isLoading } = useSWR("/ads/?is_urgent=true", apiGet<Ad[]>, {
    fallbackData: initialData ? { data: initialData } : undefined,
  });
  return {
    ads: normalize<Ad>(data?.data ?? initialData),
    error,
    isLoading,
  };
}
