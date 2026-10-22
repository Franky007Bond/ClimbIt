import type { MessageKey } from '../../i18n/messages'

export function enumMessageId(prefix: string, value: string): MessageKey {
  return `${prefix}.${value}` as MessageKey
}
