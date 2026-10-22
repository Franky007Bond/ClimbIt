import type { IntlShape } from 'react-intl'
import type { Difficulty } from '../../api/generated/types.gen'
import { en } from '../../i18n/messages'
import type { MessageKey } from '../../i18n/messages'
import { enumMessageId } from '../explore/enumLabels'

export function formatDifficultyScale(
  intl: IntlShape,
  scale: string | null,
): string | null {
  if (!scale) {
    return null
  }
  const messageId = enumMessageId('enum.difficultyScale', scale)
  if (messageId in en) {
    return intl.formatMessage({ id: messageId as MessageKey })
  }
  return scale
}

export function normalizedDifficultyGrade(difficulty: Difficulty): string {
  if (difficulty.mapped_huebler) {
    return difficulty.mapped_huebler
  }
  const value = difficulty.structured_value
  const scale = difficulty.structured_scale
  if (value && scale) {
    return `${value} (${scale})`
  }
  if (value) {
    return value
  }
  if (scale) {
    return scale
  }
  return '—'
}
