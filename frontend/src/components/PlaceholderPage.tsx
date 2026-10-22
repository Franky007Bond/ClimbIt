import { FormattedMessage } from 'react-intl'

type PlaceholderPageProps = {
  titleId: string
  bodyId: string
  bodyValues?: Record<string, string>
}

export function PlaceholderPage({
  titleId,
  bodyId,
  bodyValues,
}: PlaceholderPageProps) {
  return (
    <main>
      <h1>
        <FormattedMessage id={titleId} />
      </h1>
      <p>
        <FormattedMessage id={bodyId} values={bodyValues} />
      </p>
    </main>
  )
}
