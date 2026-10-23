import { client } from './generated/client.gen'

const configured = import.meta.env.VITE_API_BASE_URL?.trim()
const baseUrl =
  configured && configured.length > 0
    ? configured
    : import.meta.env.DEV
      ? ''
      : 'http://127.0.0.1:8000'

client.setConfig({ baseUrl })

export { client }
