"use client";

import ro from "./ro.json";

const dictionaries = {
  ro,
};

export function useI18n(locale: keyof typeof dictionaries = "ro") {
  const dict = dictionaries[locale] || ro;
  return (key: string): string => {
    const value = (dict as any)[key];
    if (value === undefined) return key;
    return String(value);
  };
}
