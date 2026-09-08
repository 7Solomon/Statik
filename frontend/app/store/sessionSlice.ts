import type { StateCreator } from 'zustand';
import type { AppStore } from './types';

/**
 * Whether the gateway would let this visitor through.
 *
 * Statik has no accounts of its own. Caddy sends a handful of paths through
 * Authelia before they reach the backend (gateway/Caddyfile, `@statik_intern`):
 * labeling, dataset generation, model training, saving and deleting systems.
 * Reading stays open so the examples work without an account.
 *
 * The probe is `/api/auth/whoami`, which sits on that protected list. What
 * matters is not what it answers but whether it answers at all:
 *
 *   200            reached the backend -> either signed in, or no gateway in
 *                  front of it (local dev, where Flask answers directly).
 *                  Nothing is restricted.
 *   anything else  something between here and the backend said no ->
 *                  restricted. Deliberately not a list of specific codes:
 *                  measured against the real gateway, an anonymous request
 *                  comes back 400, not 401, because Authelia cannot build a
 *                  redirect target without the X-Forwarded-* headers that only
 *                  the outermost proxy sets. A redirect to the portal arrives
 *                  as an opaque 0. Enumerating codes would have missed both.
 *   network error  we cannot tell, so nothing is restricted. This is the
 *                  browser-offline case, not the signed-out case: signed out
 *                  still gets a response. The real enforcement is in the
 *                  Caddyfile either way, so guessing wrong here costs a failed
 *                  request, not a hole.
 */
export const createSessionSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'session'>
> = (set) => ({
    session: {
        status: 'unknown',
        user: null,
        groups: [],
        restricted: false,

        actions: {
            load: async () => {
                try {
                    const res = await fetch('/api/auth/whoami', {
                        headers: { Accept: 'application/json' },
                        credentials: 'include',
                        cache: 'no-store',
                        // Authelia answers a browser navigation with a redirect to
                        // its portal. Following it would land on another origin and
                        // surface as an opaque CORS failure, which reads the same as
                        // "server down". Stopping here keeps the two apart.
                        redirect: 'manual',
                    });

                    if (res.ok) {
                        const data = await res.json();
                        set((state) => ({
                            session: {
                                ...state.session,
                                status: 'ready',
                                user: data.user ?? null,
                                groups: data.groups ?? [],
                                restricted: false,
                            },
                        }));
                        return;
                    }

                    set((state) => ({
                        session: {
                            ...state.session,
                            status: 'ready',
                            user: null,
                            groups: [],
                            restricted: true,
                        },
                    }));
                } catch {
                    set((state) => ({
                        session: { ...state.session, status: 'ready', restricted: false },
                    }));
                }
            },
        },
    },
});

/**
 * Where to send someone who wants to sign in.
 *
 * The gateway puts Authelia on `auth.<domain>` and Statik on `statik.<domain>`
 * (gateway/Caddyfile), so the portal is this host with its first label swapped.
 * Returns null when that shape does not hold - on localhost, for instance -
 * so no link is offered that could not work.
 */
export function authPortalUrl(): string | null {
    if (typeof window === 'undefined') return null;
    const labels = window.location.hostname.split('.');
    if (labels.length < 3) return null;
    return `${window.location.protocol}//${['auth', ...labels.slice(1)].join('.')}`;
}
