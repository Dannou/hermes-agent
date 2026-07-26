// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { MessagingEnvVarInfo, MessagingPlatformInfo } from '@/types/hermes'

const getMessagingPlatforms = vi.fn()
const updateMessagingPlatform = vi.fn()
const openExternalLink = vi.fn()

vi.mock('@/hermes', () => ({
  getMessagingPlatforms: () => getMessagingPlatforms(),
  updateMessagingPlatform: (id: string, body: unknown) => updateMessagingPlatform(id, body)
}))

vi.mock('@/lib/external-link', () => ({
  openExternalLink: (href: string) => openExternalLink(href)
}))

vi.mock('@/store/notifications', () => ({
  notify: vi.fn(),
  notifyError: vi.fn()
}))

vi.mock('@/store/system-actions', () => ({
  runGatewayRestart: vi.fn()
}))

function platform(patch: Partial<MessagingPlatformInfo> = {}): MessagingPlatformInfo {
  return {
    configured: false,
    description: 'A platform.',
    docs_url: '',
    enabled: false,
    env_vars: [],
    gateway_running: true,
    id: 'teams',
    name: 'Microsoft Teams',
    state: 'disabled',
    ...patch
  }
}

function envVar(patch: Partial<MessagingEnvVarInfo> = {}): MessagingEnvVarInfo {
  return {
    advanced: false,
    description: '',
    is_password: false,
    is_set: false,
    key: 'DISCORD_BOT_TOKEN',
    prompt: 'Discord bot token',
    redacted_value: null,
    required: true,
    url: null,
    ...patch
  }
}

beforeEach(() => {
  updateMessagingPlatform.mockResolvedValue({ ok: true, platform: 'teams' })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

async function renderMessaging() {
  const { MessagingView } = await import('./index')
  let result: ReturnType<typeof render>
  await act(async () => {
    result = render(
      <MemoryRouter>
        <MessagingView />
      </MemoryRouter>
    )
  })

  return result!
}

describe('MessagingView setup-guide link', () => {
  it('hides the setup-guide button for a plugin platform with no docs URL', async () => {
    // Teams (and other plugin platforms) ship an empty docs_url. Rendering an
    // anchor with href="" let Electron resolve it to the app's own packaged
    // index.html and fail with an OS "file not found" dialog. The button must
    // simply not appear when there is no guide to open.
    getMessagingPlatforms.mockResolvedValue({ platforms: [platform({ docs_url: '' })] })

    await renderMessaging()

    expect((await screen.findAllByText('Microsoft Teams')).length).toBeGreaterThan(0)
    expect(screen.queryByText('Open setup guide')).toBeNull()
  })

  it('opens a real docs URL through the validated external opener', async () => {
    const docsUrl = 'https://hermes-agent.nousresearch.com/docs/user-guide/messaging/teams'
    getMessagingPlatforms.mockResolvedValue({ platforms: [platform({ docs_url: docsUrl })] })

    await renderMessaging()

    const link = await screen.findByText('Open setup guide')
    await act(async () => {
      fireEvent.click(link)
    })

    await waitFor(() => expect(openExternalLink).toHaveBeenCalledWith(docsUrl))
  })
})

describe('MessagingView field surfacing', () => {
  // The Discord setup form used to list reply mode / allow-all / home channel
  // next to the bot token as four more empty boxes labelled with raw env var
  // names. They all have working defaults, so the backend now tags them
  // advanced and the form must collapse them behind the disclosure.
  it('keeps required credentials visible and hides advanced knobs until opened', async () => {
    getMessagingPlatforms.mockResolvedValue({
      platforms: [
        platform({
          env_vars: [
            envVar({ key: 'DISCORD_BOT_TOKEN', prompt: 'Discord bot token', required: true }),
            envVar({
              advanced: true,
              choices: ['off', 'first', 'all'],
              default: 'first',
              key: 'DISCORD_REPLY_TO_MODE',
              prompt: 'Discord reply mode',
              required: false
            }),
            envVar({
              advanced: true,
              default: 'Home',
              key: 'DISCORD_HOME_CHANNEL_NAME',
              prompt: 'Home channel display name',
              required: false
            })
          ],
          id: 'discord',
          name: 'Discord'
        })
      ]
    })

    await renderMessaging()

    // Labels come from the localized fieldCopy map keyed on the env var.
    expect(await screen.findByLabelText('Bot token')).toBeTruthy()
    expect(screen.queryByLabelText('Home channel name')).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByText('Advanced (2)'))
    })

    expect(screen.getByLabelText('Home channel name')).toBeTruthy()
  })

  // An empty optional box hinting only at the env var name tells the user
  // nothing about what Hermes does when it's left blank.
  it('shows the backend default instead of the raw key for a free-text knob', async () => {
    getMessagingPlatforms.mockResolvedValue({
      platforms: [
        platform({
          env_vars: [
            envVar({
              advanced: true,
              default: 'Home',
              key: 'DISCORD_HOME_CHANNEL_NAME',
              prompt: 'Home channel display name',
              required: false
            })
          ],
          id: 'discord',
          name: 'Discord'
        })
      ]
    })

    await renderMessaging()

    await act(async () => {
      fireEvent.click(await screen.findByText('Advanced (1)'))
    })

    const input = screen.getByLabelText('Home channel name') as HTMLInputElement
    expect(input.placeholder).toBe('Default: Home')
  })

  // A knob with a fixed value set is a picker, not a free-text field — typing
  // "banana" into DISCORD_REPLY_TO_MODE is silently ignored by the gateway.
  it('renders a fixed-choice knob as a picker defaulted to the backend default', async () => {
    getMessagingPlatforms.mockResolvedValue({
      platforms: [
        platform({
          env_vars: [
            envVar({
              advanced: true,
              choices: ['off', 'first', 'all'],
              default: 'first',
              key: 'DISCORD_REPLY_TO_MODE',
              prompt: 'Discord reply mode',
              required: false
            })
          ],
          id: 'discord',
          name: 'Discord'
        })
      ]
    })

    await renderMessaging()

    await act(async () => {
      fireEvent.click(await screen.findByText('Advanced (1)'))
    })

    // Radix renders the trigger as a combobox, never a free-text input.
    const control = screen.getByLabelText('Reply style')
    expect(control.getAttribute('role')).toBe('combobox')
    expect(control.tagName).not.toBe('INPUT')
    expect(control.textContent).toContain('Default (first)')
  })
})
