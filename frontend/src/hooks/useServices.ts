import useSWR from "swr";
import { apiGet } from "@/app/api/config";

export type Service = {
  id: number;
  name: string;
  description: string;
  base_price: string;
  price_type: string;
  category: { name: string };
};

export function useServices() {
  const { data, error, isLoading } = useSWR("/services/", apiGet<Service[]>);
  return {
    services: data?.data ?? [],
    error,
    isLoading,
  };
}
