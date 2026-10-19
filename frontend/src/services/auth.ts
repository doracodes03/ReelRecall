import { fetchJson } from './api';

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
}

interface AuthResponse {
  access_token: string;
  user: CurrentUser;
}

export async function authenticate(
  action: 'login' | 'register',
  payload: { email: string; password: string; full_name?: string },
): Promise<CurrentUser> {
  const response = await fetchJson<AuthResponse>(
    `/auth/${action}`,
    { method: 'POST', body: JSON.stringify(payload) },
    false,
  );
  window.localStorage.setItem('reelrecall.accessToken', response.access_token);
  return response.user;
}

export function getCurrentUser(): Promise<CurrentUser> {
  return fetchJson<CurrentUser>('/auth/me');
}

export function signOut(): void {
  window.localStorage.removeItem('reelrecall.accessToken');
}
