import useSWR from "swr";
import { apiGet } from "@/app/api/config";

export type Service = {
  id: number;
  name: string;
  description: string;
  duration_estimate_minutes: number;
  category: { name?: string };
};

const normalize = <T>(input: any): T[] => {
  if (!input) return [];
  if (Array.isArray(input)) return input;
  if (input.results) return input.results;
  return [];
};

export function useServices(initialData?: any) {
  const { data, error, isLoading } = useSWR("/services/", apiGet<Service[]>, {
    fallbackData: initialData ? { data: initialData } : undefined,
  });
  return {
    services: normalize<Service>(data?.data ?? initialData),
    error: error?.message || data?.error,
    isLoading,
  };
}
