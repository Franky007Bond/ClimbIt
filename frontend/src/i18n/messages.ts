import en from './en.json'

export type MessageKey = keyof typeof en

export const defaultLocale = 'en' as const

export const messagesByLocale = {
  en,
} as const

export { en }
